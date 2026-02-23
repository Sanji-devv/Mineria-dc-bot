import discord
from discord.ext import commands
import json
import random
from pathlib import Path
import aiohttp
import csv
import io
import urllib.parse
from typing import Tuple, List, Dict, Any

# =================================================================================================
# CONSTANTS & PATHS
# =================================================================================================

DATA_DIR = Path(__file__).parent / "datas"

# XP & Player Tracking Sheet
XP_SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKwtaT_9FOnwiCk5BtCKFJSslYUFdspL0R03AMM34vI/export?format=csv&gid=1293793215"


# Rarity color map
RARITY_COLORS = {
    "common":    discord.Color.from_rgb(150, 150, 150),  # grey
    "uncommon":  discord.Color.from_rgb(0, 180, 100),    # green
    "rare":      discord.Color.from_rgb(0, 112, 221),    # blue
    "epic":      discord.Color.from_rgb(163, 53, 238),   # purple
    "legendary": discord.Color.from_rgb(255, 128, 0),   # orange
}

RARITY_BADGES = {
    "common":    "⬜ Common",
    "uncommon":  "🟢 Uncommon",
    "rare":      "🔵 Rare",
    "epic":      "🟣 Epic",
    "legendary": "🟠 Legendary",
}

def get_rarity_color(category: str) -> discord.Color:
    return RARITY_COLORS.get(category.lower().strip(), discord.Color.blurple())

# =================================================================================================
# UTILITY COG
# =================================================================================================

class JumpToPageModal(discord.ui.Modal, title="Go to Page"):
    page_input = discord.ui.TextInput(
        label="Page Number",
        placeholder="Enter a page number...",
        min_length=1,
        max_length=4,
    )

    def __init__(self, view: "ItemPaginationView"):
        super().__init__()
        self.pagination_view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page = int(self.page_input.value) - 1
            if 0 <= page < self.pagination_view.total_pages:
                self.pagination_view.current_page = page
                self.pagination_view.update_buttons()
                await interaction.response.edit_message(embed=self.pagination_view.get_embed(), view=self.pagination_view)
            else:
                await interaction.response.send_message(
                    f"⚠️ Page must be between 1 and {self.pagination_view.total_pages}.",
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message("⚠️ Please enter a valid number.", ephemeral=True)


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
        # Hide jump button if only 1 page
        self.jump_button.disabled = (self.total_pages <= 1)

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

    @discord.ui.button(label="🔢 Jump", style=discord.ButtonStyle.primary)
    async def jump_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(JumpToPageModal(self))

class OneTimeCommands(commands.Cog):
    """
    A collection of utility commands including Loot generation, Market lookup,
    and Duplicate player detection via Google Sheets.
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
        Generates random items + coin reward based on Challenge Rating (CR).

        Args:
            cr (int): Challenge Rating (determines rarity and coin amount).
            count (int): Number of items to generate (Max 20).
        """
        # CR-based coin reward tables (min gp, max gp, silver multiplier)
        COIN_TABLE = {
            (1, 5):   (10, 150),
            (6, 10):  (100, 800),
            (11, 15): (500, 3000),
            (16, 20): (2000, 10000),
            (21, 99): (8000, 50000),
        }
        # CR-based guaranteed consumable item keywords
        CONSUMABLE_KEYWORDS = {
            (1, 5):   ["Potion of Cure Light", "Potion of Healing", "Alchemist's Fire"],
            (6, 10):  ["Potion of Cure Moderate", "Scroll", "Potion of"],
            (11, 15): ["Potion of Cure Serious", "Wand of", "Scroll of"],
            (16, 99): ["Potion of Cure Critical", "Wand of", "Elixir"],
        }

        if not self.items_data:
            self.items_data = self.load_items_data()
            if not self.items_data:
                await ctx.send("❌ Item data not found! Please check `data/items.json`.")
                return

        if count > 20:
            await ctx.send("⚠️ Max loot count is 20.")
            count = 20

        target_cats = self.get_target_categories(cr)

        # Determine coin reward
        coin_min, coin_max = 10, 100
        for (lo, hi), (cmin, cmax) in COIN_TABLE.items():
            if lo <= cr <= hi:
                coin_min, coin_max = cmin, cmax
                break
        coins = random.randint(coin_min, coin_max)

        # Determine consumable keywords for this CR tier
        consumable_kws = ["Potion"]
        for (lo, hi), kws in CONSUMABLE_KEYWORDS.items():
            if lo <= cr <= hi:
                consumable_kws = kws
                break

        # Filter items by allowable rarity categories
        possible_items = [
            item for item in self.items_data
            if item.get("category", "common").lower() in target_cats
        ]

        # Fallback Logic
        if not possible_items:
            if "epic" in target_cats:
                possible_items = [i for i in self.items_data if i.get("category", "").lower() in ["rare", "uncommon"]]
            if not possible_items:
                await ctx.send(f"❌ No items found for Rarity: {target_cats}")
                return

        # Filter consumables from the full item pool (any rarity)
        consumable_pool = [
            i for i in self.items_data
            if any(kw.lower() in i.get("name", "").lower() for kw in consumable_kws)
        ]

        # Pick embed color from highest rarity
        top_rarity = target_cats[-1] if target_cats else "common"
        embed_color = get_rarity_color(top_rarity)

        embed = discord.Embed(
            title=f"💎 Loot Generation (CR {cr})",
            description=(
                f"Rarity tier: **{', '.join(RARITY_BADGES.get(c, c.capitalize()) for c in target_cats)}**\n"
                f"Generating **{count}** item(s)"
            ),
            color=embed_color
        )

        # Generate Items
        generated_items = []
        for i in range(count):
            item_obj = random.choice(possible_items)
            name = item_obj.get("name", "Unknown Item")
            price = item_obj.get("price", 0)
            cat = item_obj.get("category", "").lower()
            badge = RARITY_BADGES.get(cat, "")

            icon = "⚔️"
            if "potion" in name.lower(): icon = "🧪"
            elif "scroll" in name.lower(): icon = "📜"
            elif "wand" in name.lower(): icon = "🪄"
            elif "ring" in name.lower(): icon = "💍"
            elif "armor" in name.lower() or "shield" in name.lower(): icon = "🛡️"

            generated_items.append(f"{icon} **{name}** ({price} gp) {badge}")

        # Bonus consumable (guaranteed)
        bonus_line = ""
        if consumable_pool:
            bonus_item = random.choice(consumable_pool)
            bonus_name = bonus_item.get("name", "Unknown")
            bonus_price = bonus_item.get("price", 0)
            bonus_line = f"🧪 **{bonus_name}** ({bonus_price} gp) *(bonus consumable)*"

        # Coin reward
        coin_line = f"🪙 **{coins:,} gp** in coins"

        # Format embed
        items_content = "\n".join([f"`{idx+1}.` {itm}" for idx, itm in enumerate(generated_items)])
        embed.add_field(name="📦 Items Found", value=items_content, inline=False)
        if bonus_line:
            embed.add_field(name="🎁 Bonus", value=bonus_line, inline=False)
        embed.add_field(name="💰 Coin Reward", value=coin_line, inline=False)
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
            cat = item.get("category", "").lower()
            badge = RARITY_BADGES.get(cat, "⬛ Unknown")
            lines.append(f"`{i+1}.` **{name}** ({price} gp) {badge}")
            
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

        # Display Item Info with rarity color
        category = match.get('category', 'unknown').lower()
        embed = discord.Embed(
            title=f"📜 {match['name']}",
            color=get_rarity_color(category)
        )
        badge = RARITY_BADGES.get(category, "⬛ Unknown")
        embed.add_field(name="💰 Price", value=f"{match.get('price', 'N/A')} gp", inline=True)
        embed.add_field(name="🏷️ Rarity", value=badge, inline=True)
        embed.add_field(name="📚 Source", value=match.get('source', 'Unknown'), inline=True)
        
        # Add d20pfsrd Link (Google CSE)
        d20_q = urllib.parse.quote_plus(match['name'])
        link = f"https://cse.google.com/cse?cx=006680642033474972217%3A6zo0hx_wle8&q={d20_q}"
        embed.add_field(name="🔗 Reference", value=f"[Wiki Search]({link})", inline=False)
        
        embed.set_footer(text="Mineria RPG • Item Database", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @item_command.command(name="filter")
    async def item_filter(self, ctx: commands.Context, *args):
        """
        Filters items by rarity and/or stat. Multiple filters can be combined.
        Usage: !item filter <rarity> [stat] or !item filter <stat> [rarity]
        Example: !item filter wis rare
        """
        STATS = {"str", "dex", "con", "int", "wis", "cha"}
        RARITY = {"common", "uncommon", "rare", "epic", "legendary"}

        if not args:
            embed = discord.Embed(title="🏷️ Filter Items", color=discord.Color.blue())
            embed.description = "Filter by rarity and/or stat — sorted cheapest to most expensive. Combine filters!"
            embed.add_field(name="Usage", value="`!item filter <Category> [Stat]`")
            embed.add_field(name="Rarity", value="`Common`, `Uncommon`, `Rare`, `Epic`, `Legendary`")
            embed.add_field(name="Stats", value="`STR`, `DEX`, `CON`, `INT`, `WIS`, `CHA`")
            embed.add_field(name="Examples", value="`!item filter rare`\n`!item filter wis`\n`!item filter wis rare`", inline=False)
            return await ctx.send(embed=embed)

        if not self.items_data:
            self.items_data = self.load_items_data()

        # Parse args: collect rarity and stat tokens
        rarity_filter = None
        stat_filters = []
        unknown_tokens = []

        for arg in args:
            norm = arg.lower().strip()
            if norm in RARITY:
                rarity_filter = norm
            elif norm in STATS:
                stat_filters.append(norm)
            else:
                unknown_tokens.append(arg)

        if unknown_tokens:
            await ctx.send(
                f"⚠️ Unknown filter(s): **{', '.join(unknown_tokens)}**\n"
                f"**Rarity:** `common` `uncommon` `rare` `epic` `legendary`\n"
                f"**Stats:** `STR` `DEX` `CON` `INT` `WIS` `CHA`"
            )
            return

        # Build title parts
        title_parts = []
        if rarity_filter:
            title_parts.append(RARITY_BADGES.get(rarity_filter, rarity_filter.capitalize()))
        if stat_filters:
            title_parts.append("+".join(s.upper() for s in stat_filters))
        title = f"🏷️ {' & '.join(title_parts)} Items (Cheap → Expensive)"

        filtered = list(self.items_data)  # start with all items

        # Apply rarity filter
        if rarity_filter:
            filtered = [i for i in filtered if i.get("category", "").lower() == rarity_filter]

        # Apply stat filter(s) — item name or description must contain ALL stat keywords
        if stat_filters:
            def matches_stats(item):
                name = item.get("name", "")
                desc = str(item.get("description", "") or item.get("bonus", "") or "")
                combined = (name + " " + desc).lower()
                return all(s in combined for s in stat_filters)
            filtered = [i for i in filtered if matches_stats(i)]

        # Sort cheapest → most expensive
        filtered.sort(key=lambda x: x.get("price", 0))

        if not filtered:
            await ctx.send(f"⚠️ No items found for: **{' + '.join(args)}**")
            return

        lines = []
        for i, item in enumerate(filtered):
            price = item.get("price", 0)
            name = item.get("name", "Unknown")
            cat = item.get("category", "").lower()
            badge = RARITY_BADGES.get(cat, "")
            lines.append(f"`{i+1}.` **{name}** ({price} gp) {badge}")

        view = ItemPaginationView(lines, title)
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

        # ── Step 4: Build Rich Embed ─────────────────────────────────────────
        has_violations = bool(violations)

        embed = discord.Embed(
            title="🔍 Duplicate Player Check",
            color=discord.Color.red() if has_violations else discord.Color.green()
        )

        # ── Summary row ──
        embed.add_field(
            name="📊 Scan Summary",
            value=(
                f"📋 Scanned: **{len(data)}** entries\n"
                f"🟢 Active:   **{len(active_chars)}** characters\n"
                f"🛌 Inactive: **{inactive_count}** (ignored)\n"
                f"⚠️  Skipped:  **{skipped}** rows (missing data)"
            ),
            inline=True
        )

        # ── Status field ──
        if has_violations:
            embed.add_field(
                name="🚨 Status",
                value=f"**{len(violations)}** player(s) in violation",
                inline=True
            )
        else:
            embed.add_field(
                name="✅ Status",
                value="All active players are **compliant**!",
                inline=True
            )

        # ── Rule reminder ──
        embed.add_field(
            name="📜 Allowed Rule",
            value="Max **1 Ranked** + **1 Clerk (Kâtip)** per player",
            inline=False
        )

        # ── Per-violation fields ──
        if has_violations:
            embed.add_field(
                name="\u200b",
                value="─" * 30,
                inline=False
            )
            for player, chars in violations.items():
                char_lines = []
                for c in chars:
                    r_lower = c['rank'].lower()
                    is_clerk = "clerk" in r_lower or "kâtip" in r_lower or "katip" in r_lower
                    role_tag = "🟡 Clerk" if is_clerk else "🔴 Ranked"
                    char_lines.append(f"{role_tag} **{c['char_name']}** — *{c['rank']}*")
                embed.add_field(
                    name=f"🚧 {player} ({len(chars)} characters)",
                    value="\n".join(char_lines),
                    inline=False
                )
        else:
            embed.add_field(
                name="✅ Result",
                value="No violations found. The server is clean! 🎉",
                inline=False
            )

        embed.set_footer(text="Mineria RPG • Rule Enforcement", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(OneTimeCommands(bot))