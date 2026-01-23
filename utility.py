import discord
from discord.ext import commands
import json
import random
from pathlib import Path
import aiohttp
import csv
import io
import difflib
from typing import Optional, Tuple, List, Dict, Any

# =================================================================================================
# CONSTANTS & PATHS
# =================================================================================================

DATA_DIR = Path(__file__).parent / "data"

# Legacy Sheet (Feat Registry)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKwtaT_9FOnwiCk5BtCKFJSslYUFdspL0R03AMM34vI/export?format=csv&gid=1512160994"

# XP & Player Tracking Sheet
XP_SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKwtaT_9FOnwiCk5BtCKFJSslYUFdspL0R03AMM34vI/export?format=csv&gid=1293793215"

# =================================================================================================
# UTILITY COG
# =================================================================================================

class OneTimeCommands(commands.Cog):
    """
    A collection of utility commands including Loot generation, Market lookup, 
    Feat registry checks, and Duplicate player detection via Google Sheets.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.items_data = self.load_items_data()

    # ==========================
    # DATA LOADING HELPERS
    # ==========================

    def load_items_data(self) -> List[Dict[str, Any]]:
        """
        Loads item data from 'data/items.json'.
        Returns a list of item dictionaries or an empty list if failed.
        """
        path = Path("data/items.json")
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
            
    def load_json(self, filename: str) -> dict:
        """
        Generic helper to load data from any JSON file in the 'data' directory.
        
        Args:
            filename (str): The name of the file (e.g., 'characters.json').
            
        Returns:
            dict: The parsed JSON data or an empty dict on failure.
        """
        path = DATA_DIR / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    async def fetch_sheet_data(self) -> List[Dict[str, Any]]:
        """
        Fetches and parses the main Feat Registry Google Sheet data.
        
        Returns:
            List[Dict]: A list of objects containing 'name' (Character Name) and 'feats' (List of feats).
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(SHEET_URL) as resp:
                if resp.status != 200:
                    return []
                content = await resp.text()
                
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows: 
            return []
        
        parsed = []
        # Parsing Logic:
        # Assumes Row 0 is header.
        # Column 1 (Index 1) is Character Name.
        # Columns 6+ contain Feats/Traits.
        for row in rows[1:]:
            if len(row) < 2: 
                continue
            
            char_name = row[1].strip()
            if not char_name: 
                continue
            
            # Collect all feats/traits from col 6 onwards
            feats = []
            if len(row) > 6:
                for cell in row[6:]:
                    cleaned = cell.strip()
                    if cleaned and cleaned != "-":
                        feats.append(cleaned)
            
            parsed.append({"name": char_name, "feats": feats})
        
        return parsed

    async def check_global_feat_legacy(self, feat_name: str, my_char_name: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if a feat is globally unique and already taken by another player in the Sheet.
        
        Args:
            feat_name (str): The name of the feat to check.
            my_char_name (str): The name of the user's current character (to avoid flagging self).
            
        Returns:
            Tuple[bool, Optional[str]]: (IsAvailable, OwnerName)
        """
        data = await self.fetch_sheet_data()
        query = feat_name.lower().strip()
        
        for entry in data:
            for f in entry["feats"]:
                val = f.lower().strip()
                
                # Check for exact match or high similarity (fuzzy match)
                # This handles typos like "Falcion" vs "Falchion"
                is_match = False
                if query == val:
                    is_match = True
                else:
                    ratio = difflib.SequenceMatcher(None, query, val).ratio()
                    if ratio > 0.85: # High threshold to avoid false positives
                        is_match = True
                
                if is_match:
                    # If found, check if it belongs to the user
                    if entry["name"].lower() == my_char_name.lower():
                        return (False, "You (in Sheet)")
                    return (False, entry["name"])
                    
        return (True, None)

    # ==========================
    # LOOT GENERATOR LOGIC
    # ==========================
    
    def get_target_categories(self, cr: int) -> List[str]:
        """Determines loot rarity categories based on Challenge Rating (CR)."""
        if cr <= 5:
            return ["common"]
        elif cr <= 10:
            return ["uncommon"]
        elif cr <= 15:
            return ["rare"]
        else:
            return ["epic", "legendary"]

    @commands.group(name="loot", invoke_without_command=True)
    async def loot_command(self, ctx: commands.Context):
        """Displays help for Loot commands."""
        embed = discord.Embed(
            title="💰 Loot Generator",
            description="Use `!loot generate <CR> [count]` to generate random loot.\nExample: `!loot generate 5 3`",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Mineria RPG • Loot System", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @loot_command.command(name="generate", aliases=["gen", "g"])
    async def generate_loot(self, ctx: commands.Context, cr: int = 1, count: int = 1):
        """
        Generates random items based on Challenge Rating (CR).
        
        Args:
            cr (int): Challenge Rating (determines rarity).
            count (int): Number of items to generate (Max 20).
        """
        # Ensure item data is loaded
        if not self.items_data:
            self.items_data = self.load_items_data()
            if not self.items_data:
                await ctx.send("❌ Item data not found! Please check `data/items.json`.")
                return

        # Cap item count to prevent spam
        if count > 20: 
            await ctx.send("⚠️ Max loot count is 20.")
            count = 20

        target_cats = self.get_target_categories(cr)
        
        # Filter items by allowable categories
        possible_items = [
            item for item in self.items_data 
            if item.get("category", "common").lower() in target_cats
        ]
        
        # Create Embed
        embed = discord.Embed(
            title=f"💎 Loot Generation (CR {cr})",
            description=f"Generating **{count}** item(s)\nRarity: **{', '.join([c.capitalize() for c in target_cats])}**",
            color=discord.Color.gold()
        )

        # Fallback Logic: If no items found for high tier, fallback to lower tiers
        if not possible_items:
            if "epic" in target_cats: 
                 possible_items = [i for i in self.items_data if i.get("category", "").lower() in ["rare", "uncommon"]]
            
            if not possible_items:
                await ctx.send(f"❌ No items found for Rarity: {target_cats}")
                return

        # Generate Items
        generated_items = []
        for i in range(count):
            item_obj = random.choice(possible_items)
            name = item_obj.get("name", "Unknown Item")
            price = item_obj.get("price", 0)
            
            # Icon selection based on keywords
            icon = "⚔️"
            if "Potion" in name: icon = "🧪"
            elif "Scroll" in name: icon = "📜"
            elif "Wand" in name: icon = "🪄"
            elif "Ring" in name: icon = "💍"
            
            generated_items.append(f"{icon} **{name}** ({price} gp)")

        # Format and Send
        content = "\n".join([f"`{idx+1}.` {itm}" for idx, itm in enumerate(generated_items)])
        embed.add_field(name="📦 Items Found", value=content, inline=False)
        embed.set_footer(text="Mineria RPG • Loot System", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    # ==========================
    # MARKET / ITEM COMMANDS
    # ==========================

    @commands.group(name="item", invoke_without_command=True)
    async def item_command(self, ctx: commands.Context):
        """Displays help for Item commands."""
        embed = discord.Embed(
            title="🔍 Item Lookup",
            description="Use `!item listdown <gold>` to find affordable items.",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Mineria RPG • Market", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @item_command.command(name="listdown")
    async def item_listdown(self, ctx: commands.Context, max_price: int):
        """
        Lists all items that cost less than or equal to the specified price.
        Shows up to 15 most expensive items fitting the criteria.
        """
        if not self.items_data:
             self.items_data = self.load_items_data()

        filtered_items = [i for i in self.items_data if i.get("price") is not None and i["price"] <= max_price]
        
        if not filtered_items:
            await ctx.send(f"⚠️ No items found for {max_price} gp or less.")
            return

        # Sort by price descending
        filtered_items.sort(key=lambda x: x["price"], reverse=True)
        
        total_count = len(filtered_items)
        display_count = min(total_count, 15)
        
        embed = discord.Embed(
            title=f"📉 Market Search (< {max_price} gp)",
            description=f"Found **{total_count}** items. Top {display_count} expensive:",
            color=discord.Color.gold()
        )
        
        lines = []
        for i, item in enumerate(filtered_items[:display_count]):
            price = item["price"]
            name = item["name"]
            cat = item.get("category", "Unknown").capitalize()
            lines.append(f"`{i+1}.` **{name}** ({price} gp) *[{cat}]*")
            
        embed.add_field(name="Items", value="\n".join(lines), inline=False)
            
        if total_count > display_count:
            embed.set_footer(text=f"...and {total_count - display_count} more • Mineria RPG", icon_url=self.bot.user.avatar.url)
        else:
            embed.set_footer(text="Mineria RPG • Market", icon_url=self.bot.user.avatar.url)
            
        await ctx.send(embed=embed)

    # ==========================
    # FEAT REGISTRY COMMANDS
    # ==========================

    @commands.group(name="feat", invoke_without_command=True)
    async def feat(self, ctx: commands.Context):
        """Feat management hub."""
        embed = discord.Embed(
            title="⚔️ Feat Registry",
            description="Use `!feat check <name>` to check global availability.",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Mineria RPG • Registry", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @feat.command(name="check")
    async def feat_check(self, ctx: commands.Context, *, query: str):
        """
        Checks if a specified feat is available in the global Google Sheet registry.
        Uses fuzzy matching to detect taken feats.
        """
        query_norm = query.strip()
        
        # User Feedback
        msg = await ctx.send(f"🔍 Checking Registry for **{query_norm}**...")
        
        # Determine "My Character Name" for self-identification
        characters = self.load_json("characters.json")
        uid = str(ctx.author.id)
        my_name = "Unknown"
        if uid in characters and characters[uid]:
            my_name = characters[uid][0]["name"]

        # Perform Check
        is_avail, owner = await self.check_global_feat_legacy(query_norm, my_name)
        
        await msg.delete()
        
        # Build Result Embed
        embed = discord.Embed(title=f"Feat Status: {query_norm}", color=discord.Color.blue())
        
        if is_avail:
             embed.title = f"✅ Available: {query_norm}"
             embed.description = "This feat is **not taken** by anyone."
             embed.color = discord.Color.green()
        else:
             embed.title = f"❌ Taken: {query_norm}"
             embed.description = f"Held by: **{owner}**"
             embed.color = discord.Color.red()
             
        embed.set_footer(text="Mineria RPG • Registry Check", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    # ==========================
    # XP & DUPLICATE PLAYER CHECK
    # ==========================

    async def fetch_xp_data(self) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetches and parses the XP Google Sheet data.
        
        Returns:
            Tuple: (List of character dicts, Count of skipped/invalid rows)
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(XP_SHEET_URL) as resp:
                if resp.status != 200: 
                    return [], 0
                content = await resp.text()
        
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows: 
            return [], 0

        skipped_count = 0
        parsed = []
        
        # Sheet Columns Assumption:
        # B (1) = Character Name
        # C (2) = Player Name
        # D (3) = XP
        # E (4) = Rank
        
        for row in rows[1:]: # Skip header
             if len(row) < 5: 
                 skipped_count += 1
                 continue
                 
             char_name = row[1].strip()
             player_name = row[2].strip()
             xp = row[3].strip()
             rank = row[4].strip()

             if not player_name or not char_name: 
                 skipped_count += 1
                 continue
             
             parsed.append({
                 "char_name": char_name,
                 "player_name": player_name,
                 "xp": xp,
                 "rank": rank
             })
             
        return parsed, skipped_count

    @commands.command(name="d", aliases=["dup", "checkdup"])
    async def duplicate_check_command(self, ctx: commands.Context):
        """
        Scans the Google Sheet for players violating character limit rules.
        
        Rules:
        - A player can have at most 2 characters.
        - If they have 2, one MUST be a Clerk (Katip) and the other Ranked.
        - 2 Ranked, 2 Clerks, or 3+ characters is a violation.
        - Inactive characters are ignored.
        """
        msg = await ctx.send("🔄 Fetching XP table data...")
        data, skipped = await self.fetch_xp_data()
        
        # Step 1: Filter Active vs Inactive
        active_chars = []
        inactive_count = 0
        
        inactive_keywords = ["inaktif", "inactive", "bıraktı", "ölü", "dead", "ayrıldı", "leave"]

        for entry in data:
            rank_str = entry["rank"].lower()
            if any(k in rank_str for k in inactive_keywords):
                inactive_count += 1
            else:
                active_chars.append(entry)

        # Step 2: Group by Player
        players = {}
        for entry in active_chars:
            p = entry["player_name"]
            if p not in players: 
                players[p] = []
            players[p].append(entry)
            
        # Step 3: Analyze Violations
        violations = {}
        
        for player, chars in players.items():
            # 0 or 1 character is always safe
            if len(chars) <= 1:
                continue
                
            # Count roles
            clerk_count = 0
            ranked_count = 0
            
            for c in chars:
                r_lower = c['rank'].lower()
                if "clerk" in r_lower or "kâtip" in r_lower or "katip" in r_lower:
                    clerk_count += 1
                else:
                    ranked_count += 1
            
            # The ONLY allowed scenario for >1 chars is: 2 Chars total (1 Ranked + 1 Clerk)
            is_valid_duo = (len(chars) == 2 and ranked_count == 1 and clerk_count == 1)
            
            if not is_valid_duo:
                 violations[player] = chars

        await msg.delete()

        # Step 4: Report Results
        embed = discord.Embed(
            title="⚠️ Illegal Duplicate Detection",
            description=(
                f"Scanned **{len(data)}** total entries.\n"
                f"Found **{len(violations)}** players violating character limits.\n"
                f"💤 **{inactive_count}** characters marked as inactive.\n"
                f"⚠️ **{skipped}** rows skipped (missing data)."
            ),
            color=discord.Color.red() if violations else discord.Color.green()
        )
        
        if not violations:
            embed.description += "\n\n✅ All active players are compliant!\n(Allowed: 1 Ranked OR 1 Ranked + 1 Clerk)"
        else:
            for player, chars in violations.items():
                char_lines = []
                for c in chars:
                    r_lower = c['rank'].lower()
                    is_clerk = "clerk" in r_lower or "kâtip" in r_lower or "katip" in r_lower
                    tag = "[CLERK]" if is_clerk else "[RANK]"
                    char_lines.append(f"• **{c['char_name']}** ({c['rank']}) {tag}")
                
                embed.add_field(name=f"🚫 {player}", value="\n".join(char_lines), inline=False)
                
        embed.set_footer(text="Mineria RPG • Rule Enforcement", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(OneTimeCommands(bot))
