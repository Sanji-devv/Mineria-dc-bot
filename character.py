import discord
from discord.ext import commands
from typing import Dict, Any, List
import re
import json
import random
from pathlib import Path

# Paths
DATA_DIR = Path("data")

def load_json(filename: str) -> dict:
    """Loads data from a JSON file in the 'data' directory."""
    path = DATA_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def save_json(filename: str, data: Any) -> None:
    """Saves data to a JSON file in the 'data' directory."""
    path = DATA_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")

def roll_stat(num_dice: int) -> List[int]:
    """Rolls N d6 and returns the top 3 results."""
    rolls = [random.randint(1, 6) for _ in range(num_dice)]
    return sorted(rolls, reverse=True)[:3]

def get_recommendations(stats: Dict[str, int]) -> List[dict]:
    """Generates class recommendations based on character stats with normalization."""
    classes = load_json("classes.json").get("classes", [])
    
    recs = []
    for cls in classes:
        primaries = cls.get("primary_stats", [])
        secondaries = cls.get("secondary_stats", [])
        
        # Calculate scores normalized by the number of required stats
        # This prevents classes with 3 primary stats (e.g., Monk) from dominating 
        # classes with 2 primary stats (e.g., Fighter) simply by having more additive terms.
        
        p_val = sum(stats.get(s, 10) for s in primaries)
        p_score = (p_val / len(primaries)) * 10 if primaries else 0
        
        s_val = sum(stats.get(s, 10) for s in secondaries)
        s_score = (s_val / len(secondaries)) * 5 if secondaries else 0
        
        total_score = p_score + s_score

        # Add slight randomization to break ties and add variety (±5%)
        # This solves the "always the exact same order" feeling
        variance = random.uniform(0.95, 1.05)
        
        recs.append({
            "name": cls.get("name", "Unknown"),
            "score": total_score * variance
        })
        
    return sorted(recs, key=lambda x: x["score"], reverse=True)[:5]

# ==========================================
# CHARACTER COG
# ==========================================

class CharacterCog(commands.Cog, name="Character"):
    def __init__(self, bot):
        self.bot = bot
        self.active_creations: Dict[int, Dict[str, Any]] = {}

    def parse_racial_modifiers(self, race_data: dict) -> Dict[str, int]:
        mods = {s: 0 for s in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]}
        stat_map = {"Strength": "STR", "Dexterity": "DEX", "Constitution": "CON", "Intelligence": "INT", "Wisdom": "WIS", "Charisma": "CHA"}
        
        for key in ["Ability Score Plus", "Ability Score Minus"]:
            text = race_data.get(key, "")
            if text and text != "None":
                for val, name in re.findall(r"([\+\-]\d+)\s+(\w+)", text):
                    if name in stat_map:
                        mods[stat_map[name]] += int(val)
        return mods

    @commands.group(name="char", invoke_without_command=True)
    async def char(self, ctx: commands.Context):
        """Character management commands."""
        embed = discord.Embed(title="👤 Character Commands", color=discord.Color.blue())
        embed.description = (
            "`!char create <race>` - Start creation\n"
            "`!char dr STR 6 DEX 5 ...` - Distribute dice\n"
            "`!char add/remove <stat> <val>` - Tweak stats\n"
            "`!char save <name>` - Finalize character\n"
            "`!char info <name>` - View character\n"
            "`!char list` - List your characters\n"
            "`!char delete <name>` - Delete character\n"
            "`!char edit class <name> <class>` - Change class\n"
            "`!char edit stat <name> <stat> <val>` - Change stat"
        )
        await ctx.send(embed=embed)

    @char.command(name="create")
    async def create(self, ctx: commands.Context, race_name: str = None):
        """Starts character creation."""
        if not race_name:
            return await ctx.send("❌ Usage: `!char create <race>` (e.g., `!char create Human`)")

        races = load_json("races.json")
        target_race = next((r for r in races if r.lower() == race_name.lower()), None)
        if not target_race:
            return await ctx.send(f"❌ Race **{race_name}** not found.")

        race_data = races[target_race]
        dice_points = 40 - race_data.get("Race Points", 10)

        self.active_creations[ctx.author.id] = {
            "race_name": target_race,
            "race_data": race_data,
            "dice_points": dice_points,
            "stats": {}
        }

        embed = discord.Embed(
            title=f"✅ {target_race} Creation Started!",
            description=f"**{ctx.author.display_name}**, your journey as a {target_race} begins.",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎲 Dice Points", value=f"You have **{dice_points}** points available.", inline=True)
        embed.add_field(name="👉 Next Step", value=f"Distribute your points using `!char dr`.\nExample: `!char dr STR 6 DEX 5 CON 5 INT 5 WIS 4 CHA 6` (Total: {dice_points} dice)", inline=False)
        
        await ctx.send(embed=embed)

    @char.command(name="dr")
    async def distribute(self, ctx: commands.Context, *args):
        """Distribute dice points and roll stats."""
        user_id = ctx.author.id
        if user_id not in self.active_creations:
            return await ctx.send("❌ Use `!char create <race>` first.")

        creation = self.active_creations[user_id]
        keys = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        stats_to_set = {}

        # Format 1: !char dr 6 5 5 5 4 5
        if len(args) == 6 and all(a.isdigit() for a in args):
            values = [int(a) for a in args]
            stats_to_set = dict(zip(keys, values))
        
        # Format 2: !char dr STR 6 DEX 5 ...
        elif len(args) == 12:
            for i in range(0, 12, 2):
                stat_name = args[i].upper()
                if stat_name not in keys:
                    return await ctx.send(f"❌ Invalid stat name: **{args[i]}**. Use STR, DEX, CON, INT, WIS, CHA.")
                if not args[i+1].isdigit():
                    return await ctx.send(f"❌ Invalid value for {stat_name}: **{args[i+1]}**. Must be a number.")
                stats_to_set[stat_name] = int(args[i+1])
            
            if len(stats_to_set) < 6:
                return await ctx.send("❌ Please provide values for ALL 6 stats: STR, DEX, CON, INT, WIS, CHA.")
        else:
            return await ctx.send(
                f"❌ **Invalid Format!**\nUse either:\n"
                f"1️⃣ `!char dr 6 5 5 5 4 5`\n"
                f"2️⃣ `!char dr STR 6 DEX 5 CON 5 INT 5 WIS 4 CHA 5`\n"
                f"Total dice points required: **{creation['dice_points']}**"
            )

        current_total = sum(stats_to_set.values())
        if current_total != creation["dice_points"]:
            diff = creation["dice_points"] - current_total
            status = "missing" if diff > 0 else "too many"
            return await ctx.send(
                f"❌ **Point Mismatch!**\n"
                f"Target: **{creation['dice_points']}** dice\n"
                f"Current: **{current_total}** dice\n"
                f"You are {status} **{abs(diff)}** dice."
            )

        if any(v < 3 for v in stats_to_set.values()):
            return await ctx.send("❌ Each stat must have at least **3** dice.")

        final_stats = {}
        racial_mods = self.parse_racial_modifiers(creation["race_data"])
        
        # --- Embed 1: Stat Roll Results ---
        embed_stats = discord.Embed(
            title=f"🎲 Stat Roll Results - {ctx.author.display_name}",
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

        embed_stats.add_field(name="📊 Roll Breakdown", value=rolls_text, inline=False)

        # Final Attributes
        attrs_text = "\n".join([f"**{s}**: {v}" for s, v in final_stats.items()])
        embed_stats.add_field(name="✨ Final Attributes", value=attrs_text, inline=True)

        # Racial Adjustments
        plus = creation["race_data"].get("Ability Score Plus", "None")
        minus = creation["race_data"].get("Ability Score Minus", "None")
        adj_text = f"**Race**: {creation['race_name']}\n**Bonus**: {plus}\n**Penalty**: {minus}"
        embed_stats.add_field(name="🛡️ Racial Traits", value=adj_text, inline=True)
        
        embed_stats.set_footer(text="Use !char save <name> to finalize your character.")

        creation["stats"] = final_stats

        # --- Embed 2: Recommended Classes ---
        embed_recs = None
        recommendations = get_recommendations(final_stats)
        if recommendations:
            embed_recs = discord.Embed(
                title="🛡️ Recommended Classes",
                description="Best matching classes:",
                color=discord.Color.blue()
            )
            rec_text = ""
            for r in recommendations:
                rec_text += f"• **{r['name']}**\n"
            embed_recs.description += f"\n\n{rec_text}"

        await ctx.send(embed=embed_stats)
        if embed_recs:
            await ctx.send(embed=embed_recs)

    @char.command(name="save")
    async def save_char(self, ctx: commands.Context, *, name: str = None):
        """Saves the character."""
        user_id = ctx.author.id
        if user_id not in self.active_creations or not self.active_creations[user_id]["stats"]:
            return await ctx.send("❌ You don't have a rolled character to save.")
        
        if not name:
            return await ctx.send("❌ Usage: `!char save <name>`")

        creation = self.active_creations[user_id]
        characters = load_json("characters.json")
        uid = str(user_id)
        
        if uid not in characters: characters[uid] = []
        if any(c["name"].lower() == name.lower() for c in characters[uid]):
            return await ctx.send(f"❌ You already have a character named **{name}**.")

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
            title="💾 Character Saved!",
            description=f"Character **{name}** has been saved to your profile!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @char.command(name="info")
    async def info(self, ctx: commands.Context, *, name: str):
        """View character info."""
        characters = load_json("characters.json")
        uid = str(ctx.author.id)
        char_data = next((c for c in characters.get(uid, []) if c["name"].lower() == name.lower()), None)
        
        if not char_data:
            return await ctx.send(f"❌ Character **{name}** not found.")
            
        embed = discord.Embed(
            title=f"🔍 Character Details - {char_data['name']}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Race", value=char_data['race'], inline=True)
        embed.add_field(name="Class", value=char_data['class'], inline=True)
        
        stats_text = "\n".join([f"**{s}**: {v}" for s, v in char_data["stats"].items()])
        embed.add_field(name="📊 Attributes", value=stats_text, inline=False)
        
        embed.set_footer(text=f"Created on {char_data['created_at'][:10]}")
        await ctx.send(embed=embed)

    @char.command(name="list")
    async def list_chars(self, ctx: commands.Context):
        """List all your characters."""
        characters = load_json("characters.json")
        user_chars = characters.get(str(ctx.author.id), [])
        
        if not user_chars:
            return await ctx.send("❌ You don't have any saved characters.")
            
        embed = discord.Embed(title="👥 Your Characters", color=discord.Color.purple())
        names = "\n".join([f"• **{c['name']}** ({c['race']} {c['class']})" for c in user_chars])
        embed.description = names
        await ctx.send(embed=embed)

    @char.command(name="delete")
    async def delete(self, ctx: commands.Context, *, name: str):
        """Delete a character."""
        characters = load_json("characters.json")
        uid = str(ctx.author.id)
        if uid not in characters: return await ctx.send("❌ No characters found.")
        
        initial = len(characters[uid])
        characters[uid] = [c for c in characters[uid] if c["name"].lower() != name.lower()]
        
        if len(characters[uid]) < initial:
            save_json("characters.json", characters)
            embed = discord.Embed(
                title="🗑️ Character Deleted",
                description=f"Character **{name}** has been permanently deleted.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Character **{name}** not found.")

    @char.command(name="rename")
    async def rename(self, ctx: commands.Context, old_name: str, new_name: str):
        """Renames an existing character."""
        characters = load_json("characters.json")
        uid = str(ctx.author.id)
        if uid not in characters: return await ctx.send("❌ No characters found.")

        for char_data in characters[uid]:
            if char_data["name"].lower() == old_name.lower():
                # Check if new name already exists
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