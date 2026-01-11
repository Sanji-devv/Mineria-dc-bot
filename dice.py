import random
import re
import discord
from discord.ext import commands

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_roll(self, expr: str):
        """Parses dice expressions (e.g., '2d20+5', '1d10', '3')."""
        expr = expr.lower().strip()
        if expr.isdigit(): return 1, int(expr), 0, f"1d{expr}"
        
        if match := re.fullmatch(r"(\d+)d(\d+)([\+\-]\d+)?", expr):
            num, sides, mod = match.groups()
            return int(num), int(sides), int(mod) if mod else 0, expr
        return None

    def roll_dice(self, num: int, sides: int, mod: int):
        """Simulates rolling specified dice."""
        rolls = [random.randint(1, sides) for _ in range(num)]
        return rolls, sum(rolls) + mod

    @commands.command(name="roll", help="Roll dice. Examples: !roll 2d20+5, !roll 1d10, !roll 20")
    async def roll(self, ctx: commands.Context, *expressions: str):
        if not expressions:
            return await ctx.send("❌ Usage: `!roll 2d20` or `!roll 1d10+5`")
        
        results = []
        for expr in expressions:
            if not (parsed := self.parse_roll(expr)):
                results.append(f"❌ `{expr}`: Invalid format!")
                continue
            
            num, sides, mod, clean_exp = parsed
            rolls, total = self.roll_dice(num, sides, mod)
            rolls_str = f"({ ' + '.join(map(str, rolls)) })" if num > 1 else ""
            mod_str = f" {'+' if mod > 0 else '-'} {abs(mod)}" if mod != 0 else ""
            results.append(f"🎲 `{clean_exp}` -> {rolls_str}{mod_str} = **{total}**")
                
        await ctx.send(embed=discord.Embed(
            title=f"🎲 {ctx.author.display_name} rolled:",
            description="\n".join(results),
            color=discord.Color.dark_grey()
        ))

async def setup(bot):
    await bot.add_cog(Dice(bot))