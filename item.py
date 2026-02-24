import discord
from discord.ext import commands
import csv
import html
import io
import json
import random
import re
import time
import aiohttp
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any

# =================================================================================================
# CONSTANTS
# =================================================================================================

# Full-name synonyms for the six ability scores
STAT_ALIASES: dict[str, list[str]] = {
    "str": ["strength",     "str"],
    "dex": ["dexterity",    "dex"],
    "con": ["constitution", "con"],
    "int": ["intelligence", "int"],
    "wis": ["wisdom",       "wis"],
    "cha": ["charisma",     "cha"],
}

def _stat_bonus_pattern(stat_key: str) -> re.Pattern:
    """
    Returns a compiled regex that matches Pathfinder bonus phrases.
    E.g. for 'wis': '+4 enhancement bonus to Wisdom'
                    'grants a +2 bonus on Wisdom'
                    'increases your Wisdom'
                    'Wisdom score by 4'
    This is intentionally broad — false positives are rare in the item set.
    """
    terms = "|".join(re.escape(t) for t in STAT_ALIASES.get(stat_key, [stat_key]))
    return re.compile(
        rf'(?:\+\d+\s+[\w\s]+?bonus\s+(?:on|to)\s+(?:{terms}))'
        rf'|(?:(?:{terms})\s+(?:score|modifier|bonus|check)s?\s+(?:by|of)\s+\d+)'
        rf'|(?:increases?(?:\s+your)?\s+(?:{terms}))'
        rf'|(?:grants?\s+a\s+\+\d+\s+[\w\s]+?\s+(?:{terms}))'
        rf'|(?:(?:{terms})\s+(?:enhancer?|enhancement))',
        re.IGNORECASE
    )

DATA_DIR = Path(__file__).parent / "datas"

RARITY_COLORS = {
    "common":    discord.Color.from_rgb(150, 150, 150),
    "uncommon":  discord.Color.from_rgb(0, 180, 100),
    "rare":      discord.Color.from_rgb(0, 112, 221),
    "epic":      discord.Color.from_rgb(163, 53, 238),
    "legendary": discord.Color.from_rgb(255, 128, 0),
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
# ITEM SHEET PARSER  (CSV columns)
# =================================================================================================

def _strip_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()

def _infer_rarity(price: int) -> str:
    if price < 1_000:   return 'common'
    if price < 5_000:   return 'uncommon'
    if price < 20_000:  return 'rare'
    if price < 60_000:  return 'epic'
    return 'legendary'

def _parse_items_csv(raw: str) -> List[Dict[str, Any]]:
    """
    Parse the Google Sheet CSV export into item dicts.
    Columns used: Name, Aura, AuraStrength, CL, Slot, Price, PriceValue,
                  Weight, Description (HTML), Destruction (requirements HTML)
    """
    reader = csv.DictReader(io.StringIO(raw))
    items = []
    for row in reader:
        name = (row.get('Name') or '').strip()
        if not name:
            continue

        # Prefer numeric PriceValue column; fall back to parsing Price string
        price_val = (row.get('PriceValue') or '').strip()
        if price_val.isdigit():
            price = int(price_val)
        else:
            m = re.search(r'([\d,]+)\s*gp', row.get('Price', ''))
            price = int(m.group(1).replace(',', '')) if m else 0

        price_str = (row.get('Price') or f'{price:,} gp').strip()

        description = _strip_html(row.get('Description') or '')
        source      = _strip_html(row.get('Destruction') or '')

        items.append({
            'name':          name,
            'price':         price,
            'price_str':     price_str,
            'category':      _infer_rarity(price),
            'slot':          (row.get('Slot')          or '').strip(),
            'aura':          (row.get('Aura')          or '').strip(),
            'aura_strength': (row.get('AuraStrength')  or '').strip(),
            'cl':            (row.get('CL')            or '').strip(),
            'weight':        (row.get('Weight')        or '').strip(),
            'description':   description,
            'source':        source,
        })
    return items

# =================================================================================================
# PAGINATION UI
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
                await interaction.response.edit_message(
                    embed=self.pagination_view.get_embed(), view=self.pagination_view
                )
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
        self.jump_button.disabled = (self.total_pages <= 1)

    def get_embed(self) -> discord.Embed:
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_items = self.items[start:end]

        embed = discord.Embed(
            title=self.title,
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

class ItemVariantSelect(discord.ui.Select):
    def __init__(self, variants: List[Dict[str, Any]], cog_ref: Any):
        self.variants = variants
        self.cog_ref = cog_ref
        
        options = []
        for i, m in enumerate(variants[:25]): # Discord max 25 options
            price_display = m.get('price_str') or f"{m.get('price', 0):,} gp"
            cat = m.get('category', '').lower()
            badge = RARITY_BADGES.get(cat, '⬛')
            # Extract emoji from badge if possible
            emoji = badge.split()[0] if badge else "⚪"
            
            label = m['name']
            if len(label) > 100: label = label[:97] + "..."
            
            desc = price_display
            if len(desc) > 100: desc = desc[:97] + "..."
            
            options.append(discord.SelectOption(
                label=label,
                description=desc,
                value=str(i),
                emoji=emoji
            ))
        super().__init__(placeholder="Select an option...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        match = self.variants[idx]
        embed = self.cog_ref.build_item_embed(match)
        await interaction.response.edit_message(embed=embed, view=self.view)

class ItemVariantView(discord.ui.View):
    def __init__(self, variants: List[Dict[str, Any]], cog_ref: Any):
        super().__init__(timeout=180)
        self.add_item(ItemVariantSelect(variants, cog_ref))

# =================================================================================================
# ITEMS COG
# =================================================================================================

class Items(commands.Cog):
    """Item lookup, loot generation, and market commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.items_data: List[Dict[str, Any]] = []

    # ── Data loading ──────────────────────────────────────────────────────────

    def _ensure_items(self) -> List[Dict[str, Any]]:
        """Return cached items from JSON. Does not auto-fetch from Google Sheets."""
        if self.items_data:
            return self.items_data
            
        json_path = DATA_DIR / "items.json"
        
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.items_data = json.load(f)
            except Exception as e:
                raise RuntimeError(f"Could not load items.json: {e}")
        else:
            raise RuntimeError("items.json not found! Please run `!item sync` first.")
            
        return self.items_data

    # ── Loot Generator ────────────────────────────────────────────────────────

    def get_target_categories(self, cr: int) -> List[str]:
        if cr <= 5:   return ["common"]
        if cr <= 10:  return ["uncommon"]
        if cr <= 15:  return ["rare"]
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
        Usage: !loot generate <CR> [count]
        """
        COIN_TABLE = {
            (1, 5):   (10, 150),
            (6, 10):  (100, 800),
            (11, 15): (500, 3000),
            (16, 20): (2000, 10000),
            (21, 99): (8000, 50000),
        }
        CONSUMABLE_KEYWORDS = {
            (1, 5):   ["Potion of Cure Light", "Potion of Healing", "Alchemist's Fire"],
            (6, 10):  ["Potion of Cure Moderate", "Scroll", "Potion of"],
            (11, 15): ["Potion of Cure Serious", "Wand of", "Scroll of"],
            (16, 99): ["Potion of Cure Critical", "Wand of", "Elixir"],
        }

        try:
            self._ensure_items()
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return
        if not self.items_data:
            await ctx.send("❌ No item data available.")
            return

        if count > 20:
            await ctx.send("⚠️ Max loot count is 20.")
            count = 20

        target_cats = self.get_target_categories(cr)

        coin_min, coin_max = 10, 100
        for (lo, hi), (cmin, cmax) in COIN_TABLE.items():
            if lo <= cr <= hi:
                coin_min, coin_max = cmin, cmax
                break
        coins = random.randint(coin_min, coin_max)

        consumable_kws = ["Potion"]
        for (lo, hi), kws in CONSUMABLE_KEYWORDS.items():
            if lo <= cr <= hi:
                consumable_kws = kws
                break

        possible_items = [
            item for item in self.items_data
            if item.get("category", "common").lower() in target_cats
        ]
        if not possible_items:
            if "epic" in target_cats:
                possible_items = [i for i in self.items_data if i.get("category", "").lower() in ["rare", "uncommon"]]
            if not possible_items:
                await ctx.send(f"❌ No items found for Rarity: {target_cats}")
                return

        consumable_pool = [
            i for i in self.items_data
            if any(kw.lower() in i.get("name", "").lower() for kw in consumable_kws)
        ]

        top_rarity = target_cats[-1] if target_cats else "common"
        embed = discord.Embed(
            title=f"💎 Loot Generation (CR {cr})",
            description=(
                f"Rarity tier: **{', '.join(RARITY_BADGES.get(c, c.capitalize()) for c in target_cats)}**\n"
                f"Generating **{count}** item(s)"
            ),
            color=get_rarity_color(top_rarity)
        )

        generated_items = []
        for _ in range(count):
            item_obj = random.choice(possible_items)
            name  = item_obj.get("name", "Unknown Item")
            price = item_obj.get("price", 0)
            cat   = item_obj.get("category", "").lower()
            badge = RARITY_BADGES.get(cat, "")
            icon  = "⚔️"
            if "potion" in name.lower():  icon = "🧪"
            elif "scroll" in name.lower(): icon = "📜"
            elif "wand" in name.lower():   icon = "🪄"
            elif "ring" in name.lower():   icon = "💍"
            elif "armor" in name.lower() or "shield" in name.lower(): icon = "🛡️"
            generated_items.append(f"{icon} **{name}** ({price} gp) {badge}")

        bonus_line = ""
        if consumable_pool:
            bonus_item  = random.choice(consumable_pool)
            bonus_name  = bonus_item.get("name", "Unknown")
            bonus_price = bonus_item.get("price", 0)
            bonus_line  = f"🧪 **{bonus_name}** ({bonus_price} gp) *(bonus consumable)*"

        coin_line = f"🪙 **{coins:,} gp** in coins"
        items_content = "\n".join([f"`{idx+1}.` {itm}" for idx, itm in enumerate(generated_items)])
        embed.add_field(name="📦 Items Found", value=items_content, inline=False)
        if bonus_line:
            embed.add_field(name="🎁 Bonus", value=bonus_line, inline=False)
        embed.add_field(name="💰 Coin Reward", value=coin_line, inline=False)
        embed.set_footer(text="Mineria RPG • Loot System", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    # ── Item Commands ─────────────────────────────────────────────────────────

    @commands.group(name="item", invoke_without_command=True)
    async def item_command(self, ctx: commands.Context):
        """Displays help for Item commands."""
        embed = discord.Embed(
            title="🔍 Item Commands",
            description=(
                "`!item sync` — download and update items.json from Google Sheets\n"
                "`!item listdown <gold|name|AC>` — sort high → low\n"
                "`!item listup <gold|name|AC>` — sort low → high\n"
                "`!item info <name>` — detailed item card\n"
                "`!item filter <rarity> [stat]` — filter by rarity/stat keyword\n"
                "`!item stat <stat>` — items that boost a stat (STR/DEX/CON/INT/WIS/CHA)\n"
                "`!item search <text>` — full-text search (name + description)\n"
                "`!item slot <slot>` — filter by equipment slot\n"
                "`!loot generate <CR> [count]` — random loot"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Mineria RPG • Market", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @item_command.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def item_sync(self, ctx: commands.Context):
        """Downloads the latest item data from Google Sheets into items.json."""
        msg = await ctx.send("🔄 Fetching Items sheet and generating JSON, please wait...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ITEMS_SHEET_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    resp.raise_for_status()
                    raw = await resp.text(encoding='utf-8-sig')
            
            items_parsed = _parse_items_csv(raw)
            if not items_parsed:
                return await msg.edit(content="❌ Fetched CSV was empty or parse failed.")
                
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(DATA_DIR / "items.json", 'w', encoding='utf-8') as f:
                json.dump(items_parsed, f, ensure_ascii=False, indent=2)
                
            self.items_data = items_parsed
            await msg.edit(content=f"✅ Items synchronized successfully! Total: **{len(items_parsed)}** items saved to `items.json`.")
            
        except Exception as exc:
            await msg.edit(content=f"❌ Sync failed! {exc}")

    async def _search_items(self, ctx: commands.Context, query: str, ascending: bool):
        """Shared logic for listdown / listup."""
        try:
            self._ensure_items()
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return

        filtered_items = []
        is_price = query.strip().isdigit()
        title = ""

        if is_price:
            max_price = int(query.strip())
            filtered_items = [i for i in self.items_data if i.get("price", 0) <= max_price]
            title = f"📉 Market Search (< {max_price} gp)"
        elif query.upper() == "AC":
            ac_keywords = [
                "armor", "shield", "plate", "mail", "scale", "leather",
                "buckler", "protection", "bracers of armor", "shirt",
                "deflection", "natural armor", "full plate", "chain"
            ]
            title = "🛡️ Armor Class Items"
            for item in self.items_data:
                if any(k in item.get("name", "").lower() for k in ac_keywords):
                    filtered_items.append(item)
        else:
            q_low_words = query.lower().strip().split()
            filtered_items = [i for i in self.items_data if all(w in i.get("name", "").lower() for w in q_low_words)]
            title = f"🔍 Item Search: '{query}'"

        if not filtered_items:
            await ctx.send(f"⚠️ No items found for '{query}'.")
            return

        filtered_items.sort(key=lambda x: x.get("price", 0), reverse=not ascending)
        title += " (Low ⬆️ High)" if ascending else " (High ⬇️ Low)"

        lines = [
            f"`{i+1}.` **{item.get('name','?')}** ({item.get('price',0)} gp) "
            f"{RARITY_BADGES.get(item.get('category','').lower(), '⬛ Unknown')}"
            for i, item in enumerate(filtered_items)
        ]
        view = ItemPaginationView(lines, title)
        await ctx.send(embed=view.get_embed(), view=view)

    @item_command.command(name="listdown")
    async def item_listdown(self, ctx: commands.Context, *, query: str = None):
        """Lists items sorted high → low. Usage: !item listdown <price|AC|name>"""
        if query is None:
            embed = discord.Embed(title="📉 Market Search (High to Low)", color=discord.Color.blue())
            embed.description = "Lists items matching your query, sorted by price (descending)."
            embed.add_field(name="Usage", value="`!item listdown <Price | AC | Name>`")
            embed.add_field(name="Examples", value="`!item listdown 500`\n`!item listdown AC`\n`!item listdown Sword`")
            return await ctx.send(embed=embed)
        await self._search_items(ctx, query, ascending=False)

    @item_command.command(name="listup")
    async def item_listup(self, ctx: commands.Context, *, query: str = None):
        """Lists items sorted low → high. Usage: !item listup <price|AC|name>"""
        if query is None:
            embed = discord.Embed(title="📈 Market Search (Low to High)", color=discord.Color.blue())
            embed.description = "Lists items matching your query, sorted by price (ascending)."
            embed.add_field(name="Usage", value="`!item listup <Price | AC | Name>`")
            embed.add_field(name="Examples", value="`!item listup 100`\n`!item listup AC`\n`!item listup Potion`")
            return await ctx.send(embed=embed)
        await self._search_items(ctx, query, ascending=True)
        
    def build_item_embed(self, match: Dict[str, Any]) -> discord.Embed:
        category = match.get('category', 'unknown').lower()
        embed = discord.Embed(title=f"📜 {match['name']}", color=get_rarity_color(category))
        badge = RARITY_BADGES.get(category, "⬛ Unknown")

        # Price — use formatted string if available
        price_display = match.get('price_str') or f"{match.get('price', 0):,} gp"
        embed.add_field(name="💰 Price",   value=price_display, inline=True)
        embed.add_field(name="🏷️ Rarity", value=badge, inline=True)

        if match.get('cl'):
            embed.add_field(name="🔮 CL", value=f"CL {match['cl']}", inline=True)
        if match.get('slot') and match['slot'] not in ('-', ''):
            embed.add_field(name="🎽 Slot", value=match['slot'].capitalize(), inline=True)
        if match.get('weight') and match['weight'] not in ('-', ''):
            embed.add_field(name="⚖️ Weight", value=match['weight'], inline=True)
        if match.get('aura'):
            aura_text = match['aura']
            if match.get('aura_strength'):
                aura_text = f"{match['aura_strength'].capitalize()} {aura_text}"
            embed.add_field(name="✨ Aura", value=aura_text, inline=False)
        if match.get('description'):
            desc = match['description']
            if len(desc) > 1024:
                desc = desc[:1021] + "…"
            embed.add_field(name="📖 Description", value=desc, inline=False)
        if match.get('source'):
            src = match['source']
            if len(src) > 512:
                src = src[:509] + "…"
            embed.add_field(name="🔨 Requirements", value=src, inline=False)

        embed.set_footer(text="Mineria RPG • Item Database", icon_url=self.bot.user.avatar.url)
        return embed

    @item_command.command(name="info")
    async def item_info(self, ctx: commands.Context, *, query: str = None):
        """Shows a detailed card for a specific item. Usage: !item info <name>"""
        if query is None:
            embed = discord.Embed(title="ℹ️ Item Information", color=discord.Color.blue())
            embed.description = "Get detailed stats for any item."
            embed.add_field(name="Usage", value="`!item info <Item Name>`")
            return await ctx.send(embed=embed)

        try:
            self._ensure_items()
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return

        query_norm = query.lower().strip()
        
        # Abbreviation mapping for common stats
        stat_aliases = {
            "str": "strength", "dex": "dexterity", "con": "constitution",
            "int": "intelligence", "wis": "wisdom", "cha": "charisma"
        }

        match = next((i for i in self.items_data if i.get("name", "").lower() == query_norm), None)

        if not match:
            # Token-based match: map abbreviations to full names, then check if all words are in the item name
            raw_words = query_norm.split()
            query_words = [stat_aliases.get(w, w) for w in raw_words]
            
            matches = [i for i in self.items_data if all(w in i.get("name", "").lower() for w in query_words)]
            
            if len(matches) == 1:
                match = matches[0]
            elif len(matches) > 1:
                matches.sort(key=lambda x: x.get('price', 0))
                # New Dropdown UI
                if len(matches) <= 25:
                    await ctx.send(
                        f"Found **{len(matches)}** variants for **{query}**. Please select one from the menu below:",
                        view=ItemVariantView(matches, self)
                    )
                else:
                    await ctx.send(f"⚠️ Found **{len(matches)}** results, exceeding Discord's drop-down limit (25). Please narrow down your search (e.g. `Belt of Giant Strength`).")
                return

        if not match:
            await ctx.send(f"❌ Item not found: **{query}**")
            return

        await ctx.send(embed=self.build_item_embed(match))

    @item_command.command(name="filter")
    async def item_filter(self, ctx: commands.Context, *args):
        """
        Filter items by rarity and/or stat.
        Usage: !item filter <rarity> [stat]
        Example: !item filter wis rare
        """
        STATS  = {"str", "dex", "con", "int", "wis", "cha"}
        RARITY = {"common", "uncommon", "rare", "epic", "legendary"}

        if not args:
            embed = discord.Embed(title="🏷️ Filter Items", color=discord.Color.blue())
            embed.description = "Filter by rarity and/or stat — sorted cheapest first."
            embed.add_field(name="Usage",   value="`!item filter <Rarity> [Stat]`")
            embed.add_field(name="Rarity",  value="`Common`, `Uncommon`, `Rare`, `Epic`, `Legendary`")
            embed.add_field(name="Stats",   value="`STR`, `DEX`, `CON`, `INT`, `WIS`, `CHA`")
            embed.add_field(name="Examples", value="`!item filter rare`\n`!item filter wis`\n`!item filter wis rare`", inline=False)
            return await ctx.send(embed=embed)

        try:
            self._ensure_items()
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return

        rarity_filter = None
        stat_filters  = []
        unknown_tokens = []

        for arg in args:
            norm = arg.lower().strip()
            if norm in RARITY:   rarity_filter = norm
            elif norm in STATS:  stat_filters.append(norm)
            else:                unknown_tokens.append(arg)

        if unknown_tokens:
            await ctx.send(
                f"⚠️ Unknown filter(s): **{', '.join(unknown_tokens)}**\n"
                f"**Rarity:** `common` `uncommon` `rare` `epic` `legendary`\n"
                f"**Stats:** `STR` `DEX` `CON` `INT` `WIS` `CHA`"
            )
            return

        title_parts = []
        if rarity_filter: title_parts.append(RARITY_BADGES.get(rarity_filter, rarity_filter.capitalize()))
        if stat_filters:  title_parts.append("+".join(s.upper() for s in stat_filters))
        title = f"🏷️ {' & '.join(title_parts)} Items (Cheap → Expensive)"

        filtered = list(self.items_data)
        if rarity_filter:
            filtered = [i for i in filtered if i.get("category", "").lower() == rarity_filter]
        if stat_filters:
            def matches_stats(item):
                combined = (item.get("name", "") + " " + str(item.get("description", ""))).lower()
                return all(s in combined for s in stat_filters)
            filtered = [i for i in filtered if matches_stats(i)]

        filtered.sort(key=lambda x: x.get("price", 0))

        if not filtered:
            await ctx.send(f"⚠️ No items found for: **{' + '.join(args)}**")
            return

        lines = [
            f"`{i+1}.` **{item.get('name','?')}** ({item.get('price',0)} gp) "
            f"{RARITY_BADGES.get(item.get('category','').lower(), '')}"
            for i, item in enumerate(filtered)
        ]
        view = ItemPaginationView(lines, title)
        await ctx.send(embed=view.get_embed(), view=view)

    @item_command.command(name="search")
    async def item_search(self, ctx: commands.Context, *, query: str = None):
        """
        Full-text search across item name AND description.
        Usage: !item search <keyword>
        """
        if not query:
            embed = discord.Embed(title="🔎 Full-Text Item Search", color=discord.Color.blue())
            embed.description = "Search across item **names and descriptions** at the same time."
            embed.add_field(name="Usage", value="`!item search <keyword>`")
            embed.add_field(name="Examples", value="`!item search poison`\n`!item search fly`\n`!item search bonus on Perception`", inline=False)
            return await ctx.send(embed=embed)

        try:
            self._ensure_items()
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return

        q = query.lower().strip()
        results = [
            item for item in self.items_data
            if q in item.get("name", "").lower()
            or q in item.get("description", "").lower()
            or q in item.get("aura", "").lower()
        ]

        if not results:
            await ctx.send(f"🔎 No items found matching **{query}**.")
            return

        results.sort(key=lambda x: (q not in x.get("name", "").lower(), x.get("price", 0)))

        lines = []
        for idx, item in enumerate(results):
            price = item.get("price", 0)
            name  = item.get("name", "Unknown")
            cat   = item.get("category", "").lower()
            badge = RARITY_BADGES.get(cat, "")
            tag   = "📛" if q in name.lower() else "📄"
            lines.append(f"`{idx+1}.` {tag} **{name}** ({price:,} gp) {badge}")

        title = f"🔎 Search: '{query}' — {len(results)} result(s)"
        view = ItemPaginationView(lines, title)
        await ctx.send(embed=view.get_embed(), view=view)

    @item_command.command(name="slot")
    async def item_slot(self, ctx: commands.Context, *, slot_query: str = None):
        """
        Filter items by equipment slot.
        Usage: !item slot <slot>
        Example: !item slot neck
        """
        KNOWN_SLOTS = [
            "head", "headband", "eyes", "shoulders", "neck", "chest",
            "body", "armor", "belt", "wrists", "hands", "ring", "feet",
            "slotless", "none",
        ]

        if not slot_query:
            embed = discord.Embed(title="🎽 Filter by Slot", color=discord.Color.blue())
            embed.description = "Find all items that occupy a specific equipment slot."
            embed.add_field(name="Usage", value="`!item slot <slot name>`")
            embed.add_field(
                name="Available Slots",
                value=", ".join(f"`{s}`" for s in KNOWN_SLOTS),
                inline=False
            )
            embed.add_field(name="Example", value="`!item slot neck`\n`!item slot ring`\n`!item slot feet`")
            return await ctx.send(embed=embed)

        try:
            self._ensure_items()
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return

        sq = slot_query.lower().strip()
        results = [item for item in self.items_data if sq in item.get("slot", "").lower()]

        if not results:
            await ctx.send(
                f"🎽 No items found for slot **{slot_query}**.\n"
                f"Try: {', '.join(f'`{s}`' for s in KNOWN_SLOTS)}"
            )
            return

        results.sort(key=lambda x: x.get("price", 0))

        lines = [
            f"`{idx+1}.` **{item.get('name','?')}** ({item.get('price',0):,} gp) "
            f"{RARITY_BADGES.get(item.get('category','').lower(), '')}"
            for idx, item in enumerate(results)
        ]
        title = f"🎽 Slot: '{slot_query.capitalize()}' — {len(results)} item(s)"
        view = ItemPaginationView(lines, title)
        await ctx.send(embed=view.get_embed(), view=view)

    @item_command.command(name="stat")
    async def item_stat(self, ctx: commands.Context, *, stat_query: str = None):
        """
        Find items that grant a bonus to a specific ability score.
        Uses Pathfinder-style bonus phrases in the item description.
        Usage: !item stat <stat>
        Example: !item stat wis  /  !item stat strength
        """
        STAT_DISPLAY = {
            "str": "Strength", "dex": "Dexterity", "con": "Constitution",
            "int": "Intelligence", "wis": "Wisdom",   "cha": "Charisma",
        }
        # Also accept full names as input
        FULL_NAME_MAP = {
            "strength": "str", "dexterity": "dex", "constitution": "con",
            "intelligence": "int", "wisdom": "wis", "charisma": "cha",
        }

        if not stat_query:
            embed = discord.Embed(title="💪 Stat-Boosting Items", color=discord.Color.blue())
            embed.description = "Find items that grant a **bonus to an ability score**."
            embed.add_field(name="Usage",  value="`!item stat <stat>`")
            embed.add_field(name="Stats",  value="`STR`, `DEX`, `CON`, `INT`, `WIS`, `CHA`")
            embed.add_field(name="Example", value="`!item stat wis`\n`!item stat strength`\n`!item stat dex`")
            return await ctx.send(embed=embed)

        sq = stat_query.lower().strip()
        # Normalise: accept full name or abbreviation
        stat_key = FULL_NAME_MAP.get(sq, sq)
        if stat_key not in STAT_DISPLAY:
            await ctx.send(
                f"⚠️ Unknown stat **{stat_query}**.\n"
                f"Use one of: `STR`, `DEX`, `CON`, `INT`, `WIS`, `CHA`"
            )
            return

        try:
            self._ensure_items()
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return

        pattern = _stat_bonus_pattern(stat_key)

        results = [
            item for item in self.items_data
            if pattern.search(item.get("description", "") or "")
            or pattern.search(item.get("name", "") or "")
        ]

        if not results:
            await ctx.send(
                f"💪 No items found that boost **{STAT_DISPLAY[stat_key]}**.\n"
                "Try `!item filter wis` for a broader keyword search."
            )
            return

        results.sort(key=lambda x: x.get("price", 0))

        lines = []
        for idx, item in enumerate(results):
            price = item.get("price", 0)
            name  = item.get("name", "Unknown")
            cat   = item.get("category", "").lower()
            badge = RARITY_BADGES.get(cat, "")
            lines.append(f"`{idx+1}.` **{name}** ({price:,} gp) {badge}")

        title = f"💪 {STAT_DISPLAY[stat_key]}-Boosting Items — {len(results)} found"
        view = ItemPaginationView(lines, title)
        await ctx.send(embed=view.get_embed(), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Items(bot))
