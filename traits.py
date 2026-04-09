import discord
from discord.ext import commands
import json
import random
from pathlib import Path

class Traits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="trait", aliases=["t"])
    async def trait(self, ctx, *categories: str):
        """Displays a random trait for each specified category."""
        traits = []
        try:
            file_path = Path(__file__).parent / "datas" / "traits.json"
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                traits = data.get("traits", [])
        except Exception:
            pass

        if not traits:
            await ctx.send("❌ Trait listesi bulunamadı.")
            return

        all_cats = list(set([t.get("category", "") for t in traits if t.get("category")]))
        
        if not categories:
            cat_list = ", ".join(all_cats)
            await ctx.send(f"❌ Kategori(ler) belirtmelisiniz.\n**Örnek:** `!trait combat social magic`\n**Mevcut Kategoriler:** `{cat_list}`")
            return

        final_categories = []
        i = 0
        while i < len(categories):
            cat = categories[i].lower()
            if cat == "random":
                count = 1
                if i + 1 < len(categories) and categories[i+1].isdigit():
                    count = int(categories[i+1])
                    i += 1
                
                # Available categories for random selection (exclude ones already chosen)
                available = [c.lower() for c in all_cats if c.lower() not in final_categories]
                count = min(count, len(available))
                if count > 0:
                    picked = random.sample(available, count)
                    final_categories.extend(picked)
            else:
                final_categories.append(cat)
            i += 1

        req_cats = final_categories
        results = []
        errors = []
        available_traits = traits.copy()

        for req_cat in req_cats:
            pool = [t for t in available_traits if t.get("category", "").lower() == req_cat]
            if pool:
                selected = random.choice(pool)
                results.append(selected)
                available_traits.remove(selected)
            else:
                errors.append(req_cat)

        if not results:
            cat_list = ", ".join(all_cats)
            await ctx.send(f"❌ Belirtilen kategori(ler) ({', '.join(errors)}) bulunamadı.\n**Mevcut Kategoriler:** `{cat_list}`")
            return

        embed = discord.Embed(
            title="🎲 Rastgele Traitler",
            description="Seçtiğiniz kategorilerden gelen traitler:",
            color=discord.Color.dark_blue()
        )

        level_labels = ["2. Seviye", "6. Seviye", "11. Seviye"]
        for i, selected in enumerate(results):
            prefix = level_labels[i] if i < len(level_labels) else f"{i + 1}."
            embed.add_field(
                name=f"{prefix} {selected.get('category', 'Bilinmeyen')} Trait: {selected.get('name', 'Bilinmeyen')}",
                value=f"**[Wiki Sayfası]({selected.get('url', '')})**",
                inline=False
            )

        footer_text = "Mineria RPG • Traits"
        if errors:
            footer_text += f" | Bulunamayanlar: {', '.join(errors)}"
        
        embed.set_footer(text=footer_text, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Traits(bot))
