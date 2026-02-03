import random
import re
import discord
from discord.ext import commands

def roll_dice(num: int, sides: int, keep: int, mod: int):
    """Simulates rolling specified dice with optional keep."""
    rolls = [random.randint(1, sides) for _ in range(num)]
    
    if keep:
        # Sort descending, take top K
        sorted_rolls = sorted(rolls, reverse=True)
        kept_rolls = sorted_rolls[:keep]
        dropped_rolls = sorted_rolls[keep:]
        total = sum(kept_rolls) + mod
        return rolls, kept_rolls, total
    else:
        total = sum(rolls) + mod
        return rolls, rolls, total

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_roll(self, expr: str):
        """Parses dice expressions (e.g., '2d20+5', '4d6k3', '1d10')."""
        expr = expr.lower().strip()
        
        # Handle single number (e.g. "20" -> 1d20)
        if expr.isdigit(): 
            sides = int(expr)
            return (1, sides, None, 0, f"1d{sides}") if sides > 0 else None
        
        # Regex for NdS [kK] [+/-M]
        # Groups: 1=Num, 2=Sides, 3=Keep, 4=Mod
        regex = r"^(\d*)d(\d+)(?:\s*k\s*(\d+))?(?:\s*([\+\-]\d+))?$"
        
        if match := re.fullmatch(regex, expr):
            num_str, sides_str, keep_str, mod_str = match.groups()
            
            num = int(num_str) if num_str else 1
            sides = int(sides_str)
            keep = int(keep_str) if keep_str else None
            mod = int(mod_str) if mod_str else 0
            
            # Safety checks
            if sides < 1: return None
            if num > 100: num = 100 
            if keep and keep > num: keep = num # Can't keep more than rolled
            
            # Reconstruct clean expression
            keep_part = f"k{keep}" if keep else ""
            mod_part = f"{'+' if mod > 0 else ''}{mod}" if mod != 0 else ""
            clean_expr = f"{num}d{sides}{keep_part}{mod_part}"
            
            return num, sides, keep, mod, clean_expr
        return None



    @commands.hybrid_command(name="roll", description="Roll dice (e.g. 1d20+5).")
    async def roll(self, ctx: commands.Context, *, expression: str = None):
        if expression is None:
            embed = discord.Embed(title="🎲 Dice Roll Help", color=discord.Color.blue())
            embed.description = "Here are some examples of how to use the roll command:"
            embed.add_field(name="Basic Roll", value="`!roll d20`\n`!roll 1d10`", inline=True)
            embed.add_field(name="With Modifier", value="`!roll 1d20+5`\n`!roll 2d6-1`", inline=True)
            embed.add_field(name="Keep Highest", value="`!roll 4d6k3` (Roll 4, keep top 3)", inline=False)
            embed.add_field(name="Multiple Rolls", value="`!roll d20, d6`", inline=False)
            await ctx.send(embed=embed)
            return

        # Allow multiple rolls separated by comma (e.g., "d20, d6")
        raw_exprs = [e.strip() for e in expression.split(",")]

        results = []
        for expr in raw_exprs:
            if not expr: continue
            
            if not (parsed := self.parse_roll(expr)):
                results.append(f"❌ `{expr}`: Invalid format (or 0 sides)!")
                continue
            
            num, sides, keep, mod, clean_exp = parsed
            all_rolls, kept_rolls, total = roll_dice(num, sides, keep, mod)
            
            mod_str = f" {'+' if mod >= 0 else '-'} {abs(mod)}" if mod != 0 else ""
            
            if keep:
                # Format: 4d6k3 -> [**6**, **5**, **5**, ~~1~~]
                sorted_rolls = sorted(all_rolls, reverse=True)
                kept_part = sorted_rolls[:keep]
                dropped_part = sorted_rolls[keep:]

                kept_formatted = [f"**{r}**" for r in kept_part]
                dropped_formatted = [f"~~{r}~~" for r in dropped_part]
                
                full_list_str = ", ".join(kept_formatted + dropped_formatted)
                results.append(f"🎲 `{clean_exp}` -> [{full_list_str}]{mod_str} = **{total}** (Top {keep})")
            else:
                rolls_str = f"({ ' + '.join(map(str, all_rolls)) })" if num > 1 else str(all_rolls[0])
                results.append(f"🎲 `{clean_exp}` -> {rolls_str}{mod_str} = **{total}**")
        
        if not results:
             return await ctx.send("❌ Usage: `!roll d6`, `!roll 2d20` or `!roll 1d10+5`")
        
        await ctx.send(embed=discord.Embed(
            title=f"🎲 {ctx.author.display_name} rolled:",
            description="\n".join(results),
            color=discord.Color.gold()
        ).set_footer(text="Mineria RPG • Dice System", icon_url=self.bot.user.avatar.url))

async def setup(bot):
    await bot.add_cog(Dice(bot))