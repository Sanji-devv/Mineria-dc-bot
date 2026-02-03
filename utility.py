import discord
from discord.ext import commands
import json
import random
from pathlib import Path
import aiohttp
import csv
import io
import difflib
import urllib.parse
from typing import Optional, Tuple, List, Dict, Any

# =================================================================================================
# CONSTANTS & PATHS
# =================================================================================================

DATA_DIR = Path(__file__).parent / "datas"

# Legacy Sheet (Feat Registry)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKwtaT_9FOnwiCk5BtCKFJSslYUFdspL0R03AMM34vI/export?format=csv&gid=1512160994"

# XP & Player Tracking Sheet
XP_SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKwtaT_9FOnwiCk5BtCKFJSslYUFdspL0R03AMM34vI/export?format=csv&gid=1293793215"

# Inventory & Market Sheet
INVENTORY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKwtaT_9FOnwiCk5BtCKFJSslYUFdspL0R03AMM34vI/export?format=csv&gid=903498896"

# =================================================================================================
# UTILITY COG
# =================================================================================================

class ItemPaginationView(discord.ui.View):
    def __init__(self, items: List[str], title: str, per_page: int = 15):
        super().__init__(timeout=180)
        self.items = items
        self.title = title
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = max(1, (len(items) + per_page - 1) // per_page)
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == self.total_pages - 1)
        self.page_counter.label = f"{self.current_page + 1}/{self.total_pages}"

    def get_embed(self) -> discord.Embed:
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_items = self.items[start:end]
        
        embed = discord.Embed(
            title=f"{self.title}",
            description=f"Found **{len(self.items)}** items.",
            color=discord.Color.gold()
        )
        
        content = "\n".join(page_items)
        embed.add_field(name="Items", value=content or "No items on this page.", inline=False)
        
        embed.set_footer(text="Mineria RPG • Market")
        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

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
        path = DATA_DIR / "items.json"
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
            if len(row) < 3: 
                continue
            
            char_name = row[2].strip()
            if not char_name: 
                continue
            
            # Collect all feats/traits from col 7 onwards (Index 7 is 1. Level Feat)
            feats = []
            if len(row) > 7:
                for cell in row[7:]:
                    cleaned = cell.strip()
                    if cleaned and cleaned != "-":
                        feats.append(cleaned)
            
            parsed.append({"name": char_name, "feats": feats})
        
        return parsed

    async def check_global_feat_legacy(self, feat_name: str, my_char_name: str) -> List[Dict[str, Any]]:
        """
        Checks if a feat is globally unique and already taken by another player in the Sheet.
        Returns a list of matches found in the registry.
        
        Args:
            feat_name (str): The name of the feat to check.
            my_char_name (str): The name of the user's current character (to avoid flagging self).
            
        Returns:
            List[Dict]: List of {"owner": str, "feat": str, "is_mine": bool}
        """
        data = await self.fetch_sheet_data()
        query = " ".join(feat_name.lower().strip().split()) # Normalize spaces
        matches = []
        
        for entry in data:
            for f in entry["feats"]:
                val = f.lower().strip()
                val_norm = " ".join(val.split()) # Normalize spaces
                
                # Check for substring match (e.g. "Weapon Focus" inside "Weapon Focus (Rapier)")
                # or fuzzy match for typos
                is_match = False
                
                if query in val_norm:
                    is_match = True
                else:
                    ratio = difflib.SequenceMatcher(None, query, val_norm).ratio()
                    if ratio > 0.85: 
                        is_match = True
                
                if is_match:
                    is_mine = (entry["name"].lower() == my_char_name.lower())
                    matches.append({
                        "owner": entry["name"],
                        "feat": f, # Return original casing
                        "is_mine": is_mine
                    })
                    
        return matches

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

    VARIABLE_FEATS = {
        "Weapon Focus",
        "Greater Weapon Focus",
        "Weapon Specialization",
        "Greater Weapon Specialization",
        "Improved Critical",
        "Skill Focus",
        "Spell Focus",
        "Greater Spell Focus",
        "Elemental Focus",
        "Greater Elemental Focus",
        "Exotic Weapon Proficiency",
        "Martial Weapon Proficiency",
        "Armor Focus", 
        "Shield Focus"
    }

    def is_common_feat(self, query: str) -> Tuple[bool, str]:
        """
        Determines if a feat is common/unlimited.
        Returns: (IsCommon, WarningMessage)
        """
        q = query.lower().strip()
        
        # 1. Check Exact/Set Matches
        for cf in self.COMMON_FEATS:
            if cf.lower() == q:
                msg = ""
                if cf.lower() == "combat casting":
                     msg = "Condition: Spell Casting Ability Modifier < 3"
                if cf.lower() == "weapon finesse":
                     msg = "⚠️ Specify a weapon (e.g., 'Weapon Finesse (Rapier)').\nRule: Cannot be taken for repeating weapons."
                return True, msg

        # 2. Check "Extra " prefix (Class Abilities)
        if q.startswith("extra "):
             return True, "Class Ability Extra Feat - Unlimited."

        # 3. Weapon/Armor Proficiency
        if "proficiency" in q and ("weapon" in q or "armor" in q or "shield" in q):
             # Exception: Exotic Weapon Proficiency is usually variable/limited
             if "exotic" not in q:
                return True, "Proficiency Feat - Unlimited."

        # 4. Teamwork Feats
        if "teamwork" in q:
             return True, "Teamwork Feat - Unlimited."

        # 5. Weapon Finesse checks (variations)
        if q.startswith("weapon finesse"):
             return True, "⚠️ Rule: Cannot be taken for repeating weapons."

        return False, ""

    async def check_global_feat_legacy(self, feat_name: str, my_char_name: str, strict: bool = False) -> List[Dict[str, Any]]:
        """
        Checks if a feat is globally unique and already taken by another player in the Sheet.
        Returns a list of matches found in the registry.
        
        Args:
            feat_name (str): The name of the feat to check.
            my_char_name (str): The name of the user's current character (to avoid flagging self).
            strict (bool): If True, disables fuzzy matching (used for Variable Feats).
            
        Returns:
            List[Dict]: List of {"owner": str, "feat": str, "is_mine": bool}
        """
        data = await self.fetch_sheet_data()
        query = " ".join(feat_name.lower().strip().split()) # Normalize spaces
        matches = []
        
        for entry in data:
            for f in entry["feats"]:
                val = f.lower().strip()
                val_norm = " ".join(val.split()) # Normalize spaces
                
                # Check for substring match (e.g. "Weapon Focus" inside "Weapon Focus (Rapier)")
                # or fuzzy match for typos
                is_match = False
                
                if query in val_norm:
                    is_match = True
                elif not strict:
                    # Only use fuzzy matching if NOT in strict mode
                    ratio = difflib.SequenceMatcher(None, query, val_norm).ratio()
                    if ratio > 0.85: 
                        is_match = True
                
                if is_match:
                    is_mine = (entry["name"].lower() == my_char_name.lower())
                    matches.append({
                        "owner": entry["name"],
                        "feat": f, # Return original casing
                        "is_mine": is_mine
                    })
                    
        return matches

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

    async def _search_items(self, ctx: commands.Context, query: str, ascending: bool):
        """
        Shared logic for listdown (descending) and listup (ascending).
        """
        if not self.items_data:
             self.items_data = self.load_items_data()

        filtered_items = []
        is_price = query.strip().isdigit()
        title = ""
        
        if is_price:
            # Price Filter Mode
            max_price = int(query.strip())
            filtered_items = [i for i in self.items_data if i.get("price") is not None and i["price"] <= max_price]
            title = f"📉 Market Search (< {max_price} gp)"
        elif query.upper() == "AC":
            # AC Mode (Heuristic)
            ac_keywords = [
                "armor", "shield", "plate", "mail", "scale", "leather", 
                "buckler", "protection", "bracers of armor", "shirt", 
                "deflection", "natural armor", "full plate", "chain"
            ]
            title = "🛡️ Armor Class Items"
            for item in self.items_data:
                name_lower = item.get("name", "").lower()
                if any(k in name_lower for k in ac_keywords):
                    filtered_items.append(item)
        else:
            # Name Search Mode
            q_low = query.lower().strip()
            filtered_items = [i for i in self.items_data if q_low in i.get("name", "").lower()]
            title = f"🔍 Item Search: '{query}'"
        
        if not filtered_items:
            await ctx.send(f"⚠️ No items found for '{query}'.")
            return

        # Sort
        # Ascending: Cheap -> Expensive
        # Descending: Expensive -> Cheap
        filtered_items.sort(key=lambda x: x.get("price", 0), reverse=not ascending)
        
        if ascending:
            title += " (Low ⬆️ High)"
        else:
            title += " (High ⬇️ Low)"

        lines = []
        for i, item in enumerate(filtered_items):
            price = item.get("price", 0)
            name = item.get("name", "Unknown")
            cat = item.get("category", "Unknown").capitalize()
            lines.append(f"`{i+1}.` **{name}** ({price} gp) *[{cat}]*")
            
        view = ItemPaginationView(lines, title)
        await ctx.send(embed=view.get_embed(), view=view)

    @item_command.command(name="listdown")
    async def item_listdown(self, ctx: commands.Context, *, query: str = None):
        """
        Lists items (Expensive -> Cheap).
        query: Price limit (int), 'AC', or Name (str).
        """
        if query is None:
            embed = discord.Embed(title="📉 Market Search (High to Low)", color=discord.Color.blue())
            embed.description = "Lists items matching your query, sorted by price (descending)."
            embed.add_field(name="Usage", value="`!item listdown <Price | AC | Name>`")
            embed.add_field(name="Examples", value="`!item listdown 500` (Max 500gp)\n`!item listdown AC` (Armor/Shields)\n`!item listdown Sword` (Name match)")
            return await ctx.send(embed=embed)

        await self._search_items(ctx, query, ascending=False)

    @item_command.command(name="listup")
    async def item_listup(self, ctx: commands.Context, *, query: str = None):
        """
        Lists items (Cheap -> Expensive).
        query: Price limit (int), 'AC', or Name (str).
        """
        if query is None:
            embed = discord.Embed(title="📈 Market Search (Low to High)", color=discord.Color.blue())
            embed.description = "Lists items matching your query, sorted by price (ascending)."
            embed.add_field(name="Usage", value="`!item listup <Price | AC | Name>`")
            embed.add_field(name="Examples", value="`!item listup 100` (Max 100gp)\n`!item listup AC` (Armor/Shields)\n`!item listup Potion` (Name match)")
            return await ctx.send(embed=embed)

        await self._search_items(ctx, query, ascending=True)

    @item_command.command(name="info")
    async def item_info(self, ctx: commands.Context, *, query: str = None):
        """
        Shows detailed information about a specific item.
        Usage: !item info <name>
        """
        if query is None:
             embed = discord.Embed(title="ℹ️ Item Information", color=discord.Color.blue())
             embed.description = "Get detailed stats and a wiki link for any item."
             embed.add_field(name="Usage", value="`!item info <Item Name>`")
             return await ctx.send(embed=embed)

        if not self.items_data:
             self.items_data = self.load_items_data()

        query_norm = query.lower().strip()
        # Exact match attempt first
        match = next((i for i in self.items_data if i.get("name", "").lower() == query_norm), None)
        
        # Fuzzy/Partial match if no exact
        if not match:
             matches = [i for i in self.items_data if query_norm in i.get("name", "").lower()]
             if len(matches) == 1:
                 match = matches[0]
             elif len(matches) > 1:
                 # Too many matches, list them
                 lines = [f"• **{m['name']}**" for m in matches[:10]]
                 embed = discord.Embed(
                     title=f"❓ Multiple matches for '{query}'",
                     description="\n".join(lines),
                     color=discord.Color.orange()
                 )
                 if len(matches) > 10:
                     embed.set_footer(text=f"and {len(matches)-10} more...")
                 await ctx.send(embed=embed)
                 return
        
        if not match:
            await ctx.send(f"❌ Item not found: **{query}**")
            return

        # Display Item Info
        embed = discord.Embed(
            title=f"📜 {match['name']}",
            color=discord.Color.blue()
        )
        embed.add_field(name="💰 Price", value=f"{match.get('price', 'N/A')} gp", inline=True)
        embed.add_field(name="🏷️ Category", value=match.get('category', 'Unknown').capitalize(), inline=True)
        embed.add_field(name="📚 Source", value=match.get('source', 'Unknown'), inline=True)
        
        # Add d20pfsrd Link (Google CSE)
        d20_q = urllib.parse.quote_plus(match['name'])
        link = f"https://cse.google.com/cse?cx=006680642033474972217%3A6zo0hx_wle8&q={d20_q}"
        embed.add_field(name="🔗 Reference", value=f"[Wiki Search]({link})", inline=False)
        
        embed.set_footer(text="Mineria RPG • Item Database", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @item_command.command(name="filter")
    async def item_filter(self, ctx: commands.Context, category: str = None):
        """
        Filters items by category (e.g. Common, Uncommon, Rare, Epic).
        Usage: !item filter <category>
        """
        if category is None:
            embed = discord.Embed(title="🏷️ Filter Items by Rarity", color=discord.Color.blue())
            embed.description = "Lists all items belonging to a specific rarity category."
            embed.add_field(name="Usage", value="`!item filter <Category>`")
            embed.add_field(name="Categories", value="`Common`, `Uncommon`, `Rare`, `Epic`, `Legendary`")
            return await ctx.send(embed=embed)

        if not self.items_data:
             self.items_data = self.load_items_data()

        cat_norm = category.lower().strip()
        filtered = [i for i in self.items_data if i.get("category", "").lower() == cat_norm]
        
        if not filtered:
             await ctx.send(f"⚠️ No items found for category: **{category}**\nValid likely categories: *common, uncommon, rare, epic, legendary*")
             return

        # Sort by price descending
        filtered.sort(key=lambda x: x.get("price", 0), reverse=True)
        
        lines = []
        for i, item in enumerate(filtered):
            price = item.get("price", 0)
            name = item.get("name", "Unknown")
            lines.append(f"`{i+1}.` **{name}** ({price} gp)")
            
        view = ItemPaginationView(lines, f"🏷️ Filter: {category.capitalize()}")
        await ctx.send(embed=view.get_embed(), view=view)

    @commands.command(name="spell")
    async def spell_lookup(self, ctx: commands.Context, *, name: str = None):
        """
        Search for a spell on d20pfsrd.
        Usage: !spell <name>
        """
        if name is None:
            embed = discord.Embed(title="🔮 Spell Lookup", color=discord.Color.purple())
            embed.description = "Quickly search for spells on the Pathfinder SRD."
            embed.add_field(name="Usage", value="`!spell <Spell Name>`")
            return await ctx.send(embed=embed)

        search_q = name.replace(" ", "+")
        link = f"https://www.d20pfsrd.com/?s={search_q}"
        
        embed = discord.Embed(
            title=f"🔮 Spell Search: {name}",
            description=f"Click below to view details on **d20pfsrd**.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="https://www.d20pfsrd.com/wp-content/uploads/sites/12/2017/01/cropped-favicon-1-192x192.png")
        embed.add_field(name="🔗 Link", value=f"[{name} on d20pfsrd]({link})", inline=False)
        embed.set_footer(text="Mineria RPG • Spellbook", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        await ctx.send(embed=embed)


    # ==========================
    # FEAT REGISTRY COMMANDS
    # ==========================

    COMMON_FEATS = {
        "Cosmopolitan",
        "Improved Unarmed Strike",
        "Precise Shot",
        "Arcane Armor Training",
        "Endurance",
        "Throw Anything",
        "Point Blank Shot",
        "Toughness", 
        "Thoughness", # User spelling
        "Combat Casting",
        "Weapon Finesse"
    }

    # is_common_feat is already defined above

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
    async def feat_check(self, ctx: commands.Context, *, query: str = None):
        """
        Checks if a specified feat is available in the global Google Sheet registry.
        Uses fuzzy or prefix matching to detect taken feats.
        """
        if query is None:
            embed = discord.Embed(title="⚔️ Check Feat Availability", color=discord.Color.green())
            embed.description = "Checks if a feat is already taken by another player or if it is common/unlimited."
            embed.add_field(name="Usage", value="`!feat check <Feat Name>`")
            return await ctx.send(embed=embed)

        query_norm = query.strip()
        
        # 1. Check for Common/Unlimited Feats FIRST
        is_common, note = self.is_common_feat(query_norm)
        if is_common:
            embed = discord.Embed(
                title=f"✅ Common Feat: {query_norm}",
                description="This feat is **Unlimited** and can be taken by anyone.",
                color=discord.Color.green()
            )
            if note:
                embed.add_field(name="Note / Condition", value=note)
            
            embed.set_footer(text="Mineria RPG • Common List", icon_url=self.bot.user.avatar.url)
            await ctx.send(embed=embed)
            return

        # 2. Check for Variable Feats (Needs Specification)
        is_variable = False
        matching_var_base = ""
        
        for vf in self.VARIABLE_FEATS:
             if query_norm.lower().startswith(vf.lower()):
                 is_variable = True
                 matching_var_base = vf
                 break
        
        # User Feedback
        msg = await ctx.send(f"🔍 Checking Registry for **{query_norm}**...")
        
        # Determine "My Character Name" for self-identification
        characters = self.load_json("characters.json")
        uid = str(ctx.author.id)
        my_name = "Unknown"
        if uid in characters and characters[uid]:
            my_name = characters[uid][0]["name"]

        if is_variable:
            # Check if user provided parens/specification
            # e.g. "Weapon Focus" -> No spec
            # e.g. "Weapon Focus (Longsword)" -> Spec
            if "(" not in query_norm or ")" not in query_norm:
                # User did NOT specify a target.
                # Instead of erroring immediately, let's list what IS taken.
                
                # Run a NON-STRICT search for the base name to find all variations
                matches = await self.check_global_feat_legacy(matching_var_base, my_name, strict=False)
                
                await msg.delete()

                embed = discord.Embed(
                    title=f"⚠️ Specification Required for {matching_var_base}",
                    description=f"**{matching_var_base}** is a variable feat. You must specify a target (e.g., `(Longsword)`).",
                    color=discord.Color.orange()
                )
                
                if matches:
                    lines = []
                    seen = set()
                    matches.sort(key=lambda x: x["owner"])
                    
                    for m in matches:
                        # Only show matches that actually start with the variable base (sanity check)
                        if matching_var_base.lower() not in m['feat'].lower():
                            continue
                             
                        unique_key = f"{m['owner']}|{m['feat']}"
                        if unique_key in seen: continue
                        seen.add(unique_key)
                        
                        owner_fmt = f"**{m['owner']}**"
                        if m['is_mine']: owner_fmt += " (You)"
                        lines.append(f"• {owner_fmt}: {m['feat']}")
                    
                    if lines:
                        desc = "\n".join(lines)
                        if len(desc) > 1000: desc = desc[:950] + "..."
                        embed.add_field(name=f"🚫 Already Taken Variations", value=desc, inline=False)
                    else:
                         embed.add_field(name="Status", value="No variations of this feat are currently taken.", inline=False)
                else:
                    embed.add_field(name="Status", value="No variations of this feat are currently taken.", inline=False)

                embed.add_field(name="Check Specific Target", value=f"To check availability, try:\n`!feat check {matching_var_base} (YourChoice)`")
                await ctx.send(embed=embed)
                return

        # Perform Check (Strict mode only if variable AND specified)
        matches = await self.check_global_feat_legacy(query_norm, my_name, strict=is_variable)
        
        await msg.delete()
        
        # Build Result Embed
        embed = discord.Embed(title=f"Feat Status: {query_norm}", color=discord.Color.blue())
        
        if not matches:
             embed.title = f"✅ Available: {query_norm}"
             embed.description = "This feat is **not taken** by anyone."
             embed.color = discord.Color.green()
        else:
             embed.title = f"FOUND: {len(matches)} matches for '{query_norm}'"
             embed.color = discord.Color.red()
             
             lines = []
             seen = set()
             
             # Sort matches by owner name for cleaner output
             matches.sort(key=lambda x: x["owner"])

             for m in matches:
                 unique_key = f"{m['owner']}|{m['feat']}"
                 if unique_key in seen:
                     continue
                 seen.add(unique_key)
                 
                 owner_fmt = f"**{m['owner']}**"
                 if m['is_mine']:
                     owner_fmt += " (You)"
                 
                 lines.append(f"• {owner_fmt}: {m['feat']}")
                 
             desc = "\n".join(lines)
             if len(desc) > 4000:
                 desc = desc[:3900] + "\n... (truncated)"
                 
             embed.description = desc
             
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

    # ==========================
    # INVENTORY COMMANDS
    # ==========================

    async def fetch_inventory_data(self) -> List[Dict[str, Any]]:
        """
        Fetches and parses the Inventory and Quality Google Sheet data.
        Updates datas/inventory.json with fresh data.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(INVENTORY_SHEET_URL) as resp:
                if resp.status != 200:
                    return []
                content = await resp.text()
                
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return []

        # Headers provided by user: Envanter, Quality, Tip, Adet, Birim Fiyatı, Tutarı, Ederi
        # We assume strict column order (0-6)
        
        parsed = []
        for row in rows[1:]: # Skip header
            if len(row) < 7:
                 continue
            
            # Map columns to keys
            item = {
                "Envanter": row[0].strip(),
                "Quality": row[1].strip(),
                "Tip": row[2].strip(),
                "Adet": row[3].strip(),
                "Birim Fiyatı": row[4].strip(),
                "Tutarı": row[5].strip(),
                "Ederi": row[6].strip()
            }
            
            # Skip empty entries if Envanter name is missing
            if not item["Envanter"]:
                continue
                
            parsed.append(item)
            
        # Save to inventory.json
        path = DATA_DIR / "inventory.json"
        try:
             with open(path, "w", encoding="utf-8") as f:
                 json.dump(parsed, f, indent=4, ensure_ascii=False)
        except IOError as e:
             print(f"Failed to save inventory.json: {e}")
             
        return parsed

    @commands.command(name="envanter", aliases=["inv", "inventory"])
    async def inventory_check(self, ctx: commands.Context, *, query: str = None):
        """
        Envanter sorgular. Veriler her sorguda anlık olarak Google Sheets'ten güncellenir.
        Kullanım: !envanter [eşya adı]
        """
        msg = await ctx.send("🔄 Envanter verileri güncelleniyor...")
        data = await self.fetch_inventory_data()
        
        if not data:
            await msg.edit(content="⚠️ Veri çekilemedi veya sayfa boş.")
            return

        if not query:
            await msg.edit(content=f"✅ Veriler güncellendi. Toplam **{len(data)}** kayıt mevcut.\nArama yapmak için: `!envanter <isim>`")
            return
            
        # Filter (Case-insensitive search in Name and Type)
        results = [
            i for i in data 
            if query.lower() in i["Envanter"].lower() or query.lower() in i["Tip"].lower()
        ]
        
        await msg.delete()
        
        if not results:
            await ctx.send(f"❌ **{query}** ile eşleşen kayıt bulunamadı.")
            return
            
        embed = discord.Embed(
            title=f"📦 Envanter Sonuçları: {query}",
            color=discord.Color.blue()
        )
        
        # Display up to 10 results
        for item in results[:10]:
            info = (
                f"**Kalite:** {item.get('Quality', '-')}\n"
                f"**Tip:** {item.get('Tip', '-')}\n"
                f"**Adet:** {item.get('Adet', '-')}\n"
                f"**Birim Fiyat:** {item.get('Birim Fiyatı', '-')}\n"
                f"**Toplam:** {item.get('Tutarı', '-')}\n"
                f"**Değer:** {item.get('Ederi', '-')}"
            )
            embed.add_field(name=f"🔹 {item.get('Envanter', '???')}", value=info, inline=True)
            
        if len(results) > 10:
            embed.set_footer(text=f"ve {len(results)-10} kayıt daha...", icon_url=self.bot.user.avatar.url)
        else:
            embed.set_footer(text="Mineria RPG • Envanter Sistemi", icon_url=self.bot.user.avatar.url)
            
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(OneTimeCommands(bot))