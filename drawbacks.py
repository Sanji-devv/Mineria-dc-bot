import discord
from discord.ext import commands
import json
import random
from pathlib import Path

class Drawbacks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.drawbacks = []
        try:
            file_path = Path(__file__).parent / "datas" / "drawbacks.json"
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.drawbacks = data.get("drawbacks", [])
        except Exception as e:
            print(f"Error loading drawbacks: {e}")

    @commands.command(name="drawback", aliases=["db"])
    async def drawback(self, ctx):
        """Displays a random drawback."""
        if not self.drawbacks:
            await ctx.send("❌ Drawback list could not be loaded.")
            return
            
        drawback = random.choice(self.drawbacks)
        
        url = drawback.get('url')
        name = drawback.get('name', 'Unknown')
        desc = f"**[{name}]({url})**" if url else f"**{name}**"
        
        embed = discord.Embed(
            title="🎲 Random Drawback",
            description=desc,
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Mineria RPG • Drawbacks", icon_url=self.bot.user.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Drawbacks(bot))
