import discord
from discord.ext import commands
import json
import random

class Links(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.drawbacks = []
        try:
            with open("datas/drawbacks.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.drawbacks = data.get("drawbacks", [])
        except Exception as e:
            print(f"Error loading drawbacks: {e}")

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
            name="🛠️ Character Creation",
            value="[Guide: Character Creation](https://mineria.fandom.com/tr/wiki/Karakter_yaratmak)",
            inline=False
        )
        
        embed.set_footer(text="Mineria RPG • Wiki", icon_url=self.bot.user.avatar.url)
        embed.set_thumbnail(url="https://static.wikia.nocookie.net/mineria/images/e/e6/Site-logo.png/revision/latest?cb=20230101000000")
        
        await ctx.send(embed=embed)

    @commands.command(name="drawback", aliases=["db"])
    async def drawback(self, ctx):
        """Displays a random drawback."""
        if not self.drawbacks:
            await ctx.send("❌ Drawback listesi şu anda yüklenemedi.")
            return
            
        drawback = random.choice(self.drawbacks)
        
        embed = discord.Embed(
            title="🎲 Rastgele Drawback",
            description=f"**[{drawback['name']}]({drawback['url']})**",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Mineria RPG • Drawbacks", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        await ctx.send(embed=embed)

    @commands.command(name="trait", aliases=["t"])
    async def trait(self, ctx, race: str = None, char_class: str = None):
        """Displays 2 random traits based on Race and Class."""
        if not race or not char_class:
            await ctx.send("Kullanım: `!t <Irk> <Sınıf>`\nÖrnek: `!t Human Fighter` veya `!t Elf Wizard`")
            return
            
        race_lower = race.lower()
        class_lower = char_class.lower()
        
        traits = []
        try:
            with open("datas/traits.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                traits = data.get("traits", [])
        except Exception:
            pass

        if not traits:
            await ctx.send("❌ Trait listesi bulunamadı.")
            return
            
        # Sadece karakterin ırkına ve sınıfına (eğer trait özellikle sınıf istiyorsa) uygun olanları filtrele
        valid_traits = [
            t for t in traits 
            if t.get("req_race", "Any").lower() in ["any", race_lower] 
            and t.get("req_class", "Any").lower() in ["any", class_lower]
        ]
        
        if not valid_traits:
            await ctx.send("❌ Uygun trait bulunamadı.")
            return
            
        # 1. Trait: Tamamen rastgele seç
        trait1 = random.choice(valid_traits)
        
        # 2. Trait: Farklı kategoriden tamamen rastgele seç
        valid_trait2_pool = [t for t in valid_traits if t["category"] != trait1["category"]]
        
        trait2 = random.choice(valid_trait2_pool) if valid_trait2_pool else None
        
        embed = discord.Embed(
            title=f"🎲 Rastgele Trait Önerisi ({race.capitalize()} {char_class.capitalize()})",
            description="Karakteriniz için uygun olabilecek 2 trait (özellik) seçildi:",
            color=discord.Color.dark_blue()
        )
        
        if trait1:
            embed.add_field(name=f"1. {trait1['category']} Trait", value=f"**[{trait1['name']}]({trait1['url']})**", inline=False)
        if trait2:
            embed.add_field(name=f"2. {trait2['category']} Trait", value=f"**[{trait2['name']}]({trait2['url']})**", inline=False)
            
        embed.set_footer(text="Mineria RPG • Traits", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Links(bot))