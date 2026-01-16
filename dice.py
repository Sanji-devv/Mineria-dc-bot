import random
import re
import discord
from discord.ext import commands

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_roll(self, expr: str):
        """Parses dice expressions (e.g., '2d20+5', '1d10', '3', 'd6')."""
        expr = expr.lower().strip()
        
        # Handle single number (e.g. "20" -> 1d20)
        if expr.isdigit(): 
            sides = int(expr)
            return (1, sides, 0, f"1d{sides}") if sides > 0 else None
        
        # Handle dice notation (e.g. "2d20", "d6", "1d10+5")
        if match := re.fullmatch(r"(\d*)d(\d+)([\+\-]\d+)?", expr):
            num_str, sides_str, mod_str = match.groups()
            
            num = int(num_str) if num_str else 1
            sides = int(sides_str)
            mod = int(mod_str) if mod_str else 0
            
            # Safety checks
            if sides < 1: return None
            if num > 100: num = 100 # Cap max dice to prevent simplified DoS
            
            # Reconstruct clean expression to reflect any caps/defaults
            mod_part = f"{'+' if mod > 0 else ''}{mod}" if mod != 0 else ""
            clean_expr = f"{num}d{sides}{mod_part}"
            
            return num, sides, mod, clean_expr
        return None

    def roll_dice(self, num: int, sides: int, mod: int):
        """Simulates rolling specified dice."""
        rolls = [random.randint(1, sides) for _ in range(num)]
        return rolls, sum(rolls) + mod

    @commands.command(name="roll", help="Roll dice. Examples: !roll d6, !roll 2d20+5, !roll 20")
    async def roll(self, ctx: commands.Context, *expressions: str):
        # Join all parts to handle spaces (e.g., "1d20 + 5")
        # Then split by comma to allow multiple rolls (e.g., "d20, d6")
        full_arg = " ".join(expressions)
        raw_exprs = [e.strip() for e in full_arg.split(",")]

        results = []
        for expr in raw_exprs:
            if not expr: continue
            
            if not (parsed := self.parse_roll(expr)):
                results.append(f"❌ `{expr}`: Invalid format (or 0 sides)!")
                continue
            
            num, sides, mod, clean_exp = parsed
            rolls, total = self.roll_dice(num, sides, mod)
            rolls_str = f"({ ' + '.join(map(str, rolls)) })" if num > 1 else ""
            mod_str = f" {'+' if mod >= 0 else '-'} {abs(mod)}" if mod != 0 else ""
            results.append(f"🎲 `{clean_exp}` -> {rolls_str}{mod_str} = **{total}**")
        
        if not results:
             return await ctx.send("❌ Usage: `!roll d6`, `!roll 2d20` or `!roll 1d10+5`")
        
        await ctx.send(embed=discord.Embed(
            title=f"🎲 {ctx.author.display_name} rolled:",
            description="\n".join(results),
            color=discord.Color.dark_grey()
        ))

async def setup(bot):
    await bot.add_cog(Dice(bot))