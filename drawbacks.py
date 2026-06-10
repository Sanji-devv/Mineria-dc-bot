import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from pathlib import Path
from typing import Optional, List

class Drawbacks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.drawbacks = []
        try:
            file_path = Path(__file__).parent / "datas" / "drawbacks.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.drawbacks = data.get("drawbacks", [])
        except Exception as e:
            print(f"Error loading drawbacks: {e}")

    async def drawback_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        names = [d.get("name", "") for d in self.drawbacks if d.get("name")]
        current_lower = current.lower()
        return [
            app_commands.Choice(name=name, value=name)
            for name in names if current_lower in name.lower()
        ][:25]

    @commands.hybrid_command(name="drawback", aliases=["db"], description="Displays a random drawback or a specific one by name.")
    @app_commands.describe(name="Specific drawback name (autocomplete list)")
    @app_commands.autocomplete(name=drawback_autocomplete)
    async def drawback(self, ctx: commands.Context, *, name: Optional[str] = None):
        """Displays a random drawback or a specific drawback by name."""
        if not self.drawbacks:
            await ctx.send("❌ Drawback list could not be loaded.")
            return

        selected_drawback = None
        if name:
            selected_drawback = next((d for d in self.drawbacks if d.get("name", "").lower() == name.lower()), None)
            if not selected_drawback:
                # Case insensitive substring search fallback
                selected_drawback = next((d for d in self.drawbacks if name.lower() in d.get("name", "").lower()), None)
            
            if not selected_drawback:
                await ctx.send(f"❌ Drawback **{name}** not found.")
                return
        else:
            selected_drawback = random.choice(self.drawbacks)
            
        url = selected_drawback.get('url')
        db_name = selected_drawback.get('name', 'Unknown')
        desc = f"**[{db_name}]({url})**" if url else f"**{db_name}**"
        
        embed = discord.Embed(
            title="🎲 Random Drawback" if not name else "📜 Drawback Details",
            description=desc,
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Mineria RPG • Drawbacks", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Drawbacks(bot))
