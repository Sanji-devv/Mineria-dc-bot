import discord
from discord.ext import commands

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["m", "mineria"])
    async def help_command(self, ctx: commands.Context):
        """Displays all available commands."""
        embed = discord.Embed(
            title="📜 Mineria Bot - Command Manual",
            description="Available commands to help you on your adventure:",
            color=discord.Color.green()
        )
        
        cmds = {
            "🎲 `!roll <expr>`": "Rolls dice. Example: `!roll 2d20+5`.",
            "🧬 `!char create <race>`": "Start creation for a race.",
            "📊 `!char dr <stats>`": "Distribute points and roll attributes.",
            "💾 `!char save <name>`": "Save your character profile.",
            "🔍 `!char info <name>`": "View details of a character.",
            "✏️ `!char rename <old> <new>`": "Rename a character.",
            "🗑️ `!char delete <name>`": "Delete a character.",
            "🛠️ `!char edit <class|stat> ...`": "Edit class or specific stats."
        }
        
        for name, val in cmds.items():
            embed.add_field(name=name, value=val, inline=False)
        
        embed.set_footer(text="Prefixes: !mineria or !m | Built for Pathfinder RPG")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
