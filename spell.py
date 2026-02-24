import discord
from discord.ext import commands
import aiohttp
import csv
import io
import json
import difflib
from pathlib import Path
from typing import List, Dict, Any

DATA_DIR = Path(__file__).parent / "datas"



# Colour map for spell schools
SCHOOL_COLORS = {
    "abjuration":    0x4FC3F7,
    "conjuration":   0x81C784,
    "divination":    0xFFD54F,
    "enchantment":   0xF06292,
    "evocation":     0xFF7043,
    "illusion":      0xCE93D8,
    "necromancy":    0x78909C,
    "transmutation": 0xA5D6A7,
    "universal":     0xB0BEC5,
}

class SpellVariantSelect(discord.ui.Select):
    def __init__(self, variants: List[Dict[str, Any]], cog_ref: Any, name_key: str):
        self.variants = variants
        self.cog_ref = cog_ref
        self.name_key = name_key
        
        options = []
        for i, m in enumerate(variants[:25]): # Discord max 25 options
            label = m.get(name_key, "Unknown").strip()
            if len(label) > 100: label = label[:97] + "..."
            
            school = m.get("School", "").strip().capitalize()
            desc = f"School: {school}" if school else "Spell"
            if len(desc) > 100: desc = desc[:97] + "..."
            
            options.append(discord.SelectOption(
                label=label,
                description=desc,
                value=str(i),
                emoji="✨"
            ))
            
        super().__init__(placeholder="Select a spell...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        match = self.variants[idx]
        embed = self.cog_ref.build_spell_embed(match, self.name_key)
        await interaction.response.edit_message(embed=embed, view=self.view)

class SpellVariantView(discord.ui.View):
    def __init__(self, variants: List[Dict[str, Any]], cog_ref: Any, name_key: str):
        super().__init__(timeout=180)
        self.add_item(SpellVariantSelect(variants, cog_ref, name_key))

class Spell(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spells_data: List[Dict[str, Any]] = []

    def _ensure_spells(self) -> List[Dict[str, Any]]:
        """Return cached spells from JSON. Does not auto-fetch from Google Sheets."""
        if self.spells_data:
            return self.spells_data
            
        json_path = DATA_DIR / "spells.json"
        
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.spells_data = json.load(f)
            except Exception as e:
                raise RuntimeError(f"Could not load spells.json: {e}")
        else:
            raise RuntimeError("spells.json not found!")
            
        return self.spells_data

    @commands.group(name="spell", invoke_without_command=True)
    async def spell_command(self, ctx, *, query: str = None):
        """Look up a spell from the Pathfinder spell list.

        Usage:
          !spell fireball          → exact / fuzzy search
          !spell                   → shows usage hint
        """
        if not query:
            embed = discord.Embed(title="✨ Spell Commands", color=discord.Color.blue())
            embed.description = (
                "`!spell <name>` — look up a spell"
            )
            embed.set_footer(text="Mineria RPG • Spells", icon_url=self.bot.user.avatar.url)
            await ctx.send(embed=embed)
            return

        try:
            rows = self._ensure_spells()
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return

        if not rows:
            return await ctx.send("❌ Spell list is empty.")

        name_key = next((k for k in rows[0].keys() if "spell name" in k.lower()), list(rows[0].keys())[0])

        q_lower = query.strip().lower()
        spell_map = {row[name_key].strip().lower(): row for row in rows if row.get(name_key)}

        # 1. Exact match (case-insensitive)
        match_row = spell_map.get(q_lower)

        # 2. Fuzzy/Substring matches
        if not match_row:
            # Check for substring matches first
            substring_matches = [row for name, row in spell_map.items() if q_lower in name]
            
            if len(substring_matches) == 1:
                match_row = substring_matches[0]
            elif len(substring_matches) > 1:
                # Provide a choice
                if len(substring_matches) <= 25:
                    return await ctx.send(
                        f"Found **{len(substring_matches)}** possible matches for **{query}**. Please select one from the menu below:",
                        view=SpellVariantView(substring_matches, self, name_key)
                    )
                else:
                    return await ctx.send(f"⚠️ Found **{len(substring_matches)}** results, exceeding Discord's drop-down limit (25). Please narrow down your search.")

            # If still not found, try difflib
            if not substring_matches:
                close = difflib.get_close_matches(q_lower, spell_map.keys(), n=5, cutoff=0.5)
                if not close:
                    return await ctx.send(
                        f"❌ Spell **{query}** not found.\n"
                        "Try a different spelling, e.g. `!spell fireball`."
                    )
                elif len(close) == 1:
                    match_row = spell_map[close[0]]
                else:
                    close_matches = [spell_map[c] for c in close]
                    return await ctx.send(
                        f"Did you mean one of these? Please select:",
                        view=SpellVariantView(close_matches, self, name_key)
                    )

        if match_row:
            await ctx.send(embed=self.build_spell_embed(match_row, name_key))



    def build_spell_embed(self, match_row: Dict[str, Any], name_key: str) -> discord.Embed:
        spell_name  = match_row.get(name_key, "Unknown").strip()
        description = match_row.get("Description", "").strip()
        school      = match_row.get("School", "").strip().lower()
        subschool   = match_row.get("Subschool", "").strip()
        casting     = match_row.get("Casting Time", "").strip()
        spell_range = match_row.get("Range", "").strip()
        duration    = match_row.get("Duration", "").strip()
        save        = match_row.get("Saving Throw", "").strip()
        sr          = match_row.get("Spell Resistance", "").strip()
        source      = match_row.get("Sourcebook", "").strip()
        targets     = match_row.get("Targets", "").strip()
        area        = match_row.get("Area", "").strip()
        effect      = match_row.get("Effect", "").strip()

        color = SCHOOL_COLORS.get(school, 0x9E9E9E)

        school_display = school.capitalize()
        if subschool and subschool not in ("—", ""):
            school_display += f" ({subschool})"

        # Mapping schools to specific emojis for the title
        school_emojis = {
            "abjuration": "🛡️",
            "conjuration": "🌀",
            "divination": "👁️",
            "enchantment": "💖",
            "evocation": "💥",
            "illusion": "🎭",
            "necromancy": "💀",
            "transmutation": "🔄",
            "universal": "🌟"
        }
        title_emoji = school_emojis.get(school, "✨")

        embed = discord.Embed(
            title=f"{title_emoji} {spell_name}",
            color=color
        )

        if description:
            desc_trimmed = description if len(description) <= 1024 else description[:1021] + "…"
            embed.add_field(name="📜 Description", value=desc_trimmed, inline=False)

        stats_parts = []
        if school_display: stats_parts.append(f"🎓 **School:** {school_display}")
        if casting:        stats_parts.append(f"⏱️ **Casting Time:** {casting}")
        if spell_range:    stats_parts.append(f"📏 **Range:** {spell_range}")
        
        for emoji, label, val in [("🎯", "Targets", targets), ("⭕", "Area", area), ("✨", "Effect", effect)]:
            if val and val not in ("—", ""):
                stats_parts.append(f"{emoji} **{label}:** {val}")
                
        if duration:       stats_parts.append(f"⏳ **Duration:** {duration}")
        if save:           stats_parts.append(f"🎲 **Saving Throw:** {save}")
        if sr:             stats_parts.append(f"🛡️ **Spell Resistance:** {sr}")

        if stats_parts:
            embed.add_field(name="📋 Details", value="\n".join(stats_parts), inline=False)

        class_columns = [
            "Arcanist", "Wizard", "Sorcerer", "Witch", "Magus", "Bard",
            "Skald", "Summoner", "Druid", "Hunter", "Ranger", "Cleric",
            "Oracle", "Warpriest", "Inquisitor", "Antipaladin", "Paladin",
            "Alchemist", "Investigator", "Psychic", "Mesmerist",
            "Occultist", "Spiritualist", "Medium", "Bloodrager", "Shaman",
        ]
        class_levels = []
        for cls in class_columns:
            val = match_row.get(cls, "—").strip()
            if val and val not in ("—", ""):
                class_levels.append(f"**{cls}** {val}")

        if class_levels:
            embed.add_field(
                name="🧙 Class Levels",
                value=", ".join(class_levels),
                inline=False
            )

        if source and source not in ("—", ""):
            embed.set_footer(text=f"Mineria RPG • Source: {source}", icon_url=self.bot.user.avatar.url)
        else:
            embed.set_footer(text="Mineria RPG • Spell List", icon_url=self.bot.user.avatar.url)

        return embed


async def setup(bot):
    await bot.add_cog(Spell(bot))
