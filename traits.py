import discord
from discord.ext import commands
import json
import random
from pathlib import Path

class Traits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.traits = []
        try:
            file_path = Path(__file__).parent / "datas" / "traits.json"
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.traits = data.get("traits", [])
        except Exception as e:
            print(f"Error loading traits: {e}")

    @commands.command(name="trait", aliases=["t"])
    async def trait(self, ctx, *args: str):
        """Displays a random trait for each specified category. Requires race specification."""
        traits = self.traits.copy()

        if not traits:
            await ctx.send("❌ Trait list not found.")
            return

        race = None
        categories = []
        for arg in args:
            if arg.lower().startswith("race(") and arg.endswith(")"):
                race = arg[5:-1].strip().lower()
            else:
                categories.append(arg)

        all_cats = sorted(list(set([t.get("category", "") for t in traits if t.get("category")])))
        display_cats = [cat if cat != "Race" else "Race(human)" for cat in all_cats]
        cat_list = ", ".join(display_cats)

        if not race or not categories:
            error_prefix = "❌ You must specify both a race and category(s)." if not race and not categories else \
                          "❌ You must specify a race." if not race else \
                          "❌ You must specify category(s)."
            
            example_race = race if race else "human"
            hint_message = (
                f"{error_prefix}\n"
                f"**Example:** `!trait race({example_race}) combat social`\n"
                f"**Available Categories:** `{cat_list}`"
            )
            await ctx.send(hint_message)
            return

        # Filter traits by race
        filtered_traits = [t for t in traits if t.get("req_race", "Any").lower() in ["any", race]]

        final_categories = []
        i = 0
        while i < len(categories):
            cat = categories[i].lower()
            if cat == "random":
                count = 1
                if i + 1 < len(categories) and categories[i+1].isdigit():
                    count = int(categories[i+1])
                    i += 1
                
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
        available_traits = filtered_traits.copy()

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
            await ctx.send(f"❌ Specified category(s) ({', '.join(errors)}) not found for race `{race}`.\n**Available Categories:** `{cat_list}`")
            return

        embed = discord.Embed(
            title="🎲 Random Traits",
            description=f"Traits for race **{race.capitalize()}** from your selected categories:",
            color=discord.Color.dark_blue()
        )

        level_labels = ["Level 2", "Level 6", "Level 11"]
        for i, selected in enumerate(results):
            prefix = level_labels[i] if i < len(level_labels) else f"{i + 1}."
            embed.add_field(
                name=f"{prefix} {selected.get('category', 'Unknown')} Trait: {selected.get('name', 'Unknown')}",
                value=f"**[Wiki Page]({selected.get('url', '')})**",
                inline=False
            )

        footer_text = "Mineria RPG • Traits"
        if errors:
            footer_text += f" | Not found: {', '.join(errors)}"
        
        embed.set_footer(text=footer_text, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Traits(bot))
