import discord
from discord.ext import commands

class Links(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="wiki", aliases=["link"])
    async def links(self, ctx):
        """Displays important Mineria Wiki links."""
        embed = discord.Embed(
            title="📚 Mineria Wiki Links",
            description="Official resources for Mineria RPG",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🏠 Wiki Homepage",
            value="[Mineria Wiki](https://mineria.fandom.com/tr/wiki/Mineria_Wiki)",
            inline=False
        )
        
        embed.add_field(
            name="📝 Character Page Guide",
            value="[Character Sheet Template](https://mineria.fandom.com/tr/wiki/TaslakKarakterKagidi?so=search)",
            inline=False
        )

        embed.add_field(
            name="🛠️ Karakter Yaratma",
            value="[Rehber: Karakter Yaratmak](https://mineria.fandom.com/tr/wiki/Karakter_yaratmak)",
            inline=False
        )
        
        embed.set_footer(text="Mineria RPG • Wiki", icon_url=self.bot.user.avatar.url)
        embed.set_thumbnail(url="https://static.wikia.nocookie.net/mineria/images/e/e6/Site-logo.png/revision/latest?cb=20230101000000")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Links(bot))