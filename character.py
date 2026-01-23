import discord
from discord.ext import commands
from typing import Dict, Any, List, Optional, Tuple, Union
import re
import json
import random
import statistics
from pathlib import Path

# =================================================================================================
# CONSTANTS & PATHS
# =================================================================================================

DATA_DIR = Path(__file__).parent / "data"

# Standard Feat Slots fallback
DEFAULT_FEAT_SLOTS = [
    "1. Level", "1. Level Class Bonus Feat", "1. Level Racial Bonus Feat",
    "3. Level", "5. Level", "7. Level", "9. Level", "11. Level"
]

# =================================================================================================
# HELPER FUNCTIONS
# =================================================================================================

def load_json(filename: str) -> Union[Dict, List, Any]:
    """Loads JSON data from the data directory safely."""
    path = DATA_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_json(filename: str, data: Any) -> None:
    """Saves data to a JSON file in the data directory."""
    path = DATA_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")

def roll_stat(num_dice: int) -> List[int]:
    """Rolls N d6 and returns the top 3 results."""
    rolls = [random.randint(1, 6) for _ in range(num_dice)]
    return sorted(rolls, reverse=True)[:3]

def get_recommendations(stats: Dict[str, int]) -> List[dict]:
    """
    Generates class recommendations based on stats.
    Returns: List of dicts with 'name' and 'score'.
    """
    classes_data = load_json("classes.json")
    if isinstance(classes_data, dict):
        classes = classes_data.get("classes", [])
    else:
        classes = []

    recs = []
    for cls in classes:
        primaries = cls.get("primary_stats", [])
        secondaries = cls.get("secondary_stats", [])
        
        # Helper to get values for a list of stats
        get_vals = lambda slist: [stats.get(s, 10) for s in slist]

        # Score Calculation
        p_score = statistics.mean(get_vals(primaries)) * 1.0 if primaries else 0
        s_score = statistics.mean(get_vals(secondaries)) * 0.5 if secondaries else 0
        
        total_score = p_score + s_score
        
        # Add slight randomization to break ties
        variance = random.uniform(0.95, 1.05)
        
        recs.append({
            "name": cls.get("name", "Unknown"),
            "score": total_score * variance
        })
        
    return sorted(recs, key=lambda x: x["score"], reverse=True)[:5]

# =================================================================================================
# CHARACTER COG
# =================================================================================================

class CharacterCog(commands.Cog, name="Character"):
    """
    Commands for Character Creation, Management, and Stat Rolling.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_creations: Dict[int, Dict[str, Any]] = {}

    def parse_racial_modifiers(self, race_data: dict) -> Dict[str, int]:
        """
        Parses racial attribute modifiers from text descriptions.
        Example: "+2 Strength, -2 Wisdom" -> {'STR': 2, 'WIS': -2}
        """
        mods = {s: 0 for s in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]}
        
        stat_map = {
            "Strength": "STR", "Dexterity": "DEX", "Constitution": "CON", 
            "Intelligence": "INT", "Wisdom": "WIS", "Charisma": "CHA"
        }
        
        regex = r"([\+\-]\d+)\s*(\w+)"
        
        for key in ["Ability Score Plus", "Ability Score Minus"]:
            text = race_data.get(key, "")
            if text and text not in ["None", ""]:
                
                # Check for "Any" bonus
                if "to one ability score" in text.lower():
                     mods["ANY"] = 2

                for val, name in re.findall(regex, text):
                    # Match full names or short codes
                    for full_name, short_code in stat_map.items():
                        if full_name.lower() in name.lower() or short_code.lower() == name.lower():
                            mods[short_code] += int(val)
                            break
        return mods

    # ==========================
    # MAIN COMMAND GROUP
    # ==========================

    @commands.group(name="char", invoke_without_command=True)
    async def char(self, ctx: commands.Context):
        """Root command for Character Management."""
        embed = discord.Embed(title="👤 Character Commands", color=discord.Color.gold())
        embed.description = (
            "**Creation**\n"
            "`!char create <race>` - Start creation\n"
            "`!char dr <stats>` - Distribute dice\n"
            "`!char add/remove <stat> <val>` - Tweak stats\n"
            "`!char save <name>` - Finalize character\n\n"
            "**Management**\n"
            "`!char info [name]` - View character\n"
            "`!char list` - List your characters\n"
            "`!char rename <old> <new>` - Rename\n"
            "`!char delete <name>` - Delete\n\n"
            "**Editing**\n"
            "`!char edit class <name> <class>`\n"
            "`!char edit stat <name> <stat> <val>`"
        )
        embed.set_footer(text="Mineria RPG • Character System", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    # ==========================
    # CREATION FLOW
    # ==========================

    @char.command(name="create")
    async def create(self, ctx: commands.Context, race_name: str = None):
        """
        Initiates the character creation process for a given race.
        Usage: !char create Human
        """
        if not race_name:
            return await ctx.send("❌ Usage: `!char create <race>` (e.g., `!char create Human`)")

        races = load_json("races.json")
        target_race = next((r for r in races if r.lower() == race_name.lower()), None)
        if not target_race:
            return await ctx.send(f"❌ Race **{race_name}** not found.")

        # Setup Creation Context
        race_data = races[target_race]
        dice_points = 40 - race_data.get("Race Points", 10)

        self.active_creations[ctx.author.id] = {
            "race_name": target_race,
            "race_data": race_data,
            "dice_points": dice_points,
            "stats": {}
        }

        embed = discord.Embed(
            title=f"✨ {target_race} Creation Started",
            description=f"**{ctx.author.display_name}**, your journey begins.",
            color=discord.Color.gold()
        )
        embed.add_field(name="🎲 Dice Points", value=f"**{dice_points}** points available.", inline=True)
        embed.add_field(name="👉 Next Step", value="Distribute using `!char dr`.\nEx: `!char dr STR 10 DEX 10 ...`", inline=False)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_footer(text="Mineria RPG • Creation Mode", icon_url=self.bot.user.avatar.url)
        
        await ctx.send(embed=embed)

    @char.command(name="dr")
    async def distribute(self, ctx: commands.Context, *args):
        """
        Distributes dice points and rolls for stats.
        Usage: !char dr STR 6 DEX 6 ... (Total dice must match available points)
        """
        user_id = ctx.author.id
        if user_id not in self.active_creations:
            return await ctx.send("❌ Use `!char create <race>` first.")

        creation = self.active_creations[user_id]
        keys = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        stats_to_set = {}

        # Parse Arguments
        # Mode 1: Pure numbers "6 6 6 6 6 6" (Assumes order: STR DEX CON INT WIS CHA)
        if len(args) == 6 and all(a.isdigit() for a in args):
            values = [int(a) for a in args]
            stats_to_set = dict(zip(keys, values))
        
        # Mode 2: Key-Value pairs "STR 6 DEX 6..."
        elif len(args) == 12:
            for i in range(0, 12, 2):
                stat_name = args[i].upper()
                if stat_name not in keys:
                    return await ctx.send(f"❌ Invalid stat name: **{args[i]}**.")
                if not args[i+1].isdigit():
                    return await ctx.send(f"❌ Invalid value for {stat_name}: **{args[i+1]}**.")
                stats_to_set[stat_name] = int(args[i+1])
            
            if len(stats_to_set) < 6:
                return await ctx.send("❌ Please provide values for ALL 6 stats.")
        else:
            return await ctx.send(
                f"❌ **Invalid Format!**\nUse `!char dr STR 6 ...` (Target Total: {creation['dice_points']})"
            )

        # Validation
        current_total = sum(stats_to_set.values())
        if current_total != creation["dice_points"]:
            diff = creation["dice_points"] - current_total
            status = "missing" if diff > 0 else "too many"
            return await ctx.send(
                f"❌ **Point Mismatch!**\n"
                f"Target: **{creation['dice_points']}** | Current: **{current_total}**\n"
                f"You are {status} **{abs(diff)}** dice."
            )

        if any(v < 3 for v in stats_to_set.values()):
            return await ctx.send("❌ Each stat must have at least **3** dice.")

        # Roll Logic
        final_stats = {}
        racial_mods = self.parse_racial_modifiers(creation["race_data"])
        
        embed_stats = discord.Embed(
            title="🎲 Stat Roll Results",
            description=f"Rolled by **{ctx.author.display_name}**",
            color=discord.Color.gold()
        )

        rolls_text = ""
        for stat, num in stats_to_set.items():
            top_rolls = roll_stat(num)
            base_total = sum(top_rolls)
            mod = racial_mods.get(stat, 0)
            final_val = base_total + mod
            final_stats[stat] = final_val
            
            mod_str = f" {'+' if mod >= 0 else '-'} {abs(mod)} (Race)" if mod != 0 else ""
            rolls_text += f"**{stat}**: ({num}d6) -> {base_total}{mod_str} = **{final_val}**\n"

        embed_stats.add_field(name="📊 Details", value=rolls_text, inline=False)

        # Display Stats
        phy = ["STR", "DEX", "CON"]
        men = ["INT", "WIS", "CHA"]
        
        col1 = "\n".join([f"**{s}**: {final_stats[s]}" for s in phy])
        col2 = "\n".join([f"**{s}**: {final_stats[s]}" for s in men])
        
        embed_stats.add_field(name="🛡️ Physical", value=col1, inline=True)
        embed_stats.add_field(name="🔮 Mental", value=col2, inline=True)

        # Racial info
        plus = creation["race_data"].get("Ability Score Plus", "None")
        minus = creation["race_data"].get("Ability Score Minus", "None")
        adj_text = f"**Race**: {creation['race_name']}\n**Bonus**: {plus}\n**Penalty**: {minus}"
        
        if racial_mods.get("ANY"):
            adj_text += f"\n\n✨ **Flexible Bonus!**\nUse `!char add <STAT> {racial_mods['ANY']}`"
        
        embed_stats.add_field(name="🧬 Traits", value=adj_text, inline=False)
        embed_stats.set_footer(text="Use !char save <name> to finalize.", icon_url=self.bot.user.avatar.url)

        creation["stats"] = final_stats
        await ctx.send(embed=embed_stats)

        # Recommendations
        settings = load_json("user_settings.json")
        user_settings = settings.get(str(ctx.author.id), {})
        
        if user_settings.get("show_recommendations", True):
            recommendations = get_recommendations(final_stats)
            if recommendations:
                embed_recs = discord.Embed(
                    title="🛡️ Class Recommendations",
                    description="\n".join([f"• **{r['name']}**" for r in recommendations]),
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed_recs)

    @char.command(name="add")
    async def add_stat(self, ctx: commands.Context, stat: str, value: int):
        """Adds a bonus value to a stat during creation."""
        user_id = ctx.author.id
        if user_id not in self.active_creations:
             return await ctx.send("❌ No active character creation.")
        
        creation = self.active_creations[user_id]
        if "stats" not in creation or not creation["stats"]:
             return await ctx.send("❌ Roll stats first with `!char dr`.")

        stat = stat.upper()
        if stat not in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            return await ctx.send("❌ Invalid stat.")

        creation["stats"][stat] += value
        await ctx.send(f"✅ **{stat}** updated to **{creation['stats'][stat]}**")

    @char.command(name="remove")
    async def remove_stat(self, ctx: commands.Context, stat: str, value: int):
        """Removes a value from a stat during creation."""
        user_id = ctx.author.id
        if user_id not in self.active_creations:
             return await ctx.send("❌ No active character creation.")
        
        creation = self.active_creations[user_id]
        if not creation.get("stats"):
             return await ctx.send("❌ Roll stats first.")

        stat = stat.upper()
        if stat not in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            return await ctx.send("❌ Invalid stat.")

        creation["stats"][stat] -= value
        await ctx.send(f"✅ **{stat}** updated to **{creation['stats'][stat]}**")

    @char.command(name="save")
    async def save_char(self, ctx: commands.Context, *, name: str = None):
        """Finalizes and saves the character."""
        user_id = ctx.author.id
        if user_id not in self.active_creations or not self.active_creations[user_id]["stats"]:
            return await ctx.send("❌ No pending creation to save. Use `!char create`.")
        
        if not name: return await ctx.send("❌ Usage: `!char save <name>`")

        creation = self.active_creations[user_id]
        characters = load_json("characters.json")
        uid = str(user_id)
        
        if uid not in characters: characters[uid] = []
        if any(c["name"].lower() == name.lower() for c in characters[uid]):
            return await ctx.send(f"❌ Name **{name}** is taken.")

        new_char = {
            "name": name,
            "race": creation["race_name"],
            "class": "None",
            "stats": creation["stats"],
            "created_at": str(ctx.message.created_at)
        }
        
        characters[uid].append(new_char)
        save_json("characters.json", characters)
        del self.active_creations[user_id]
        
        embed = discord.Embed(
            title="💾 Character Saved",
            description=f"**{name}** ({creation['race_name']}) has been created!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Mineria RPG • Saved", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    # ==========================
    # REC SETTINGS
    # ==========================
    
    @commands.group(name="rec", invoke_without_command=True)
    async def rec(self, ctx: commands.Context):
        """Settings for Class Recommendations."""
        await ctx.send("Use `!rec open` or `!rec close`.")

    @rec.command(name="open")
    async def rec_open(self, ctx: commands.Context):
        """Enables class recommendations."""
        settings = load_json("user_settings.json")
        uid = str(ctx.author.id)
        if uid not in settings: settings[uid] = {}
        settings[uid]["show_recommendations"] = True
        save_json("user_settings.json", settings)
        await ctx.send("✅ Recommendations **Enabled**.")

    @rec.command(name="close")
    async def rec_close(self, ctx: commands.Context):
        """Disables class recommendations."""
        settings = load_json("user_settings.json")
        uid = str(ctx.author.id)
        if uid not in settings: settings[uid] = {}
        settings[uid]["show_recommendations"] = False
        save_json("user_settings.json", settings)
        await ctx.send("❌ Recommendations **Disabled**.")

    # ==========================
    # EDITING COMMANDS
    # ==========================

    @char.group(name="edit", invoke_without_command=True)
    async def edit(self, ctx: commands.Context):
        """Edit saved character details."""
        await ctx.send("❌ Usage: `!char edit class` or `!char edit stat`")

    @edit.command(name="class")
    async def edit_class(self, ctx: commands.Context, name: str, new_class: str):
        """Edits a character's class."""
        characters = load_json("characters.json")
        uid = str(ctx.author.id)
        if uid not in characters: return await ctx.send("❌ No characters.")

        char_data = next((c for c in characters[uid] if c["name"].lower() == name.lower()), None)
        if not char_data: return await ctx.send(f"❌ Character **{name}** not found.")

        old_class = char_data.get("class", "None")
        char_data["class"] = new_class
        save_json("characters.json", characters)
        
        embed = discord.Embed(
            title="✏️ Class Updated",
            description=f"**{char_data['name']}**: {old_class} ➡️ **{new_class}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @edit.command(name="stat")
    async def edit_stat(self, ctx: commands.Context, name: str, stat: str, value: int):
        """Edits a character's specific stat."""
        characters = load_json("characters.json")
        uid = str(ctx.author.id)
        if uid not in characters: return await ctx.send("❌ No characters.")

        char_data = next((c for c in characters[uid] if c["name"].lower() == name.lower()), None)
        if not char_data: return await ctx.send(f"❌ Character **{name}** not found.")

        stat = stat.upper()
        if stat not in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            return await ctx.send("❌ Invalid stat.")

        old_val = char_data["stats"].get(stat, 0)
        char_data["stats"][stat] = value
        save_json("characters.json", characters)
        
        embed = discord.Embed(
            title="✏️ Stat Updated",
            description=f"**{char_data['name']}** {stat}: {old_val} ➡️ **{value}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # ==========================
    # ROSTER / INFO
    # ==========================

    @char.command(name="info")
    async def info(self, ctx: commands.Context, *, name: str = None):
        """Detailed view of a character."""
        characters = load_json("characters.json")
        uid = str(ctx.author.id)
        user_chars = characters.get(uid, [])
        
        if not user_chars:
            return await ctx.send("❌ You don't have any saved characters.")

        char_data = None
        if name is None:
            if len(user_chars) == 1:
                char_data = user_chars[0]
            else:
                char_list = ", ".join([f"`{c['name']}`" for c in user_chars])
                embed = discord.Embed(
                    title="🔢 Multiple Characters Found",
                    description=f"Please specify which one:\n\n{char_list}\n\nUsage: `!char info <name>`",
                    color=discord.Color.gold()
                )
                return await ctx.send(embed=embed)
        else:
            char_data = next((c for c in user_chars if c["name"].lower() == name.lower()), None)
        
        if not char_data:
            return await ctx.send(f"❌ Character **{name}** not found.")
            
        char_class = char_data.get('class', 'Adventurer')
        if char_class == "None": char_class = "Adventurer"
        
        embed = discord.Embed(
            title=f"📜 {char_data['name']}",
            description=f"✨ **{char_data['race']}** • **{char_class}**",
            color=discord.Color.gold()
        )

        # Stats Visualizer
        stats = char_data.get("stats", {})
        def fmt_stat(label, key, emoji):
            val = stats.get(key, 10)
            mod = (val - 10) // 2
            sign = "+" if mod >= 0 else ""
            return f"{emoji} **{label}**: {val} (`{sign}{mod}`)"

        col1 = [fmt_stat("STR", "STR", "💪"), fmt_stat("DEX", "DEX", "🏃"), fmt_stat("CON", "CON", "❤️")]
        col2 = [fmt_stat("INT", "INT", "🧠"), fmt_stat("WIS", "WIS", "🦉"), fmt_stat("CHA", "CHA", "🎭")]

        embed.add_field(name="🛡️ Physical", value="\n".join(col1), inline=True)
        embed.add_field(name="🔮 Mental", value="\n".join(col2), inline=True)
        
        # Feat Display
        feats = char_data.get("feats", {})
        if feats:
            feat_lines = []
            for slot, feat in feats.items():
                short_slot = slot.replace("Level", "Lvl").replace("Bonus Feat", "Bonus")
                feat_lines.append(f"• **{short_slot}**: {feat}")
            
            feats_text = "\n".join(feat_lines)
            if len(feats_text) > 1000: feats_text = feats_text[:990] + "..."
            embed.add_field(name="⚔️ Known Feats", value=feats_text, inline=False)
        else:
            embed.add_field(name="⚔️ Known Feats", value=" ", inline=False)

        created_at = char_data.get("created_at", "").split(" ")[0]
        footer_text = f"Mineria RPG • Created: {created_at}"
        embed.set_footer(text=footer_text, icon_url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)
        if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
            
        await ctx.send(embed=embed)

    @char.command(name="list")
    async def list_chars(self, ctx: commands.Context):
        """Lists all characters owned by the user."""
        characters = load_json("characters.json")
        user_chars = characters.get(str(ctx.author.id), [])
        
        if not user_chars:
            return await ctx.send("❌ You don't have any saved characters.")
            
        embed = discord.Embed(
            title="👥 Your Characters", 
            color=discord.Color.gold()
        )
        names = "\n".join([f"• **{c['name']}** ({c['race']} {c['class']})" for c in user_chars])
        embed.description = names
        embed.set_footer(text="Mineria RPG • Roster", icon_url=self.bot.user.avatar.url)
        if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @char.command(name="rename")
    async def rename(self, ctx: commands.Context, old_name: str, new_name: str):
        """Renames a character."""
        characters = load_json("characters.json")
        uid = str(ctx.author.id)
        if uid not in characters: return await ctx.send("❌ No characters found.")

        for char_data in characters[uid]:
            if char_data["name"].lower() == old_name.lower():
                # Check duplication
                if any(c["name"].lower() == new_name.lower() for c in characters[uid]):
                    return await ctx.send(f"❌ You already have a character named **{new_name}**.")
                
                char_data["name"] = new_name
                save_json("characters.json", characters)
                embed = discord.Embed(
                    title="✏️ Character Renamed",
                    description=f"Character **{old_name}** renamed to **{new_name}**.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return
        
        await ctx.send(f"❌ Character **{old_name}** not found.")

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))