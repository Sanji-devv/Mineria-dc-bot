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
        """Displays a random trait for each specified category.
        Race specification is only needed if 'Race' category is requested.
        Usage: !trait combat social  OR  !trait race(human) combat social
        """
        traits = self.traits.copy()

        if not traits:
            await ctx.send("❌ Trait list not found.")
            return

        # --- Parse arguments ---
        race = None
        categories = []

        for arg in args:
            arg_lower = arg.lower().strip()
            if arg_lower.startswith("race(") and arg_lower.endswith(")"):
                race = arg_lower[5:-1].strip()
            else:
                categories.append(arg_lower)

        all_cats = sorted(list(set([t.get("category", "") for t in traits if t.get("category")])))
        # Show Race as Race(human) in category hint
        display_cats = [cat if cat != "Race" else "Race(human)" for cat in all_cats]
        cat_list = ", ".join(display_cats)

        # Determine if user requested a Race category
        wants_race_trait = "race" in [c.lower() for c in categories]

        if not args:
            hint_message = (
                f"❌ You must specify at least 3 different categories.\n"
                f"**Usage:** `!trait combat social magic`  or  `!trait race(human) combat social`\n"
                f"**Available Categories:** `{cat_list}`"
            )
            await ctx.send(hint_message)
            return

        if wants_race_trait and not race:
            hint_message = (
                f"❌ You must specify a race when requesting a Race trait.\n"
                f"**Usage:** `!trait race(human) combat social`\n"
                f"**Available Categories:** `{cat_list}`"
            )
            await ctx.send(hint_message)
            return

        # --- Build final category list (handles "random" keyword) ---
        final_categories = []
        i = 0
        while i < len(categories):
            cat = categories[i]
            if cat == "random":
                count = 1
                if i + 1 < len(categories) and categories[i + 1].isdigit():
                    count = int(categories[i + 1])
                    i += 1
                available = [c.lower() for c in all_cats if c.lower() != "race" and c.lower() not in final_categories]
                count = min(count, len(available))
                if count > 0:
                    picked = random.sample(available, count)
                    final_categories.extend(picked)
            else:
                # Skip if user manually typed "race" — it's handled automatically
                if cat != "race":
                    final_categories.append(cat)
            i += 1

        # --- Enforce at least 3 different categories ---
        total_traits = len(set(final_categories)) + (1 if race else 0)
        if total_traits < 3:
            hint_message = (
                f"❌ You must specify at least 3 different categories.\n"
                f"**Usage:** `!trait combat social magic`  or  `!trait race(human) combat social`\n"
                f"**Available Categories:** `{cat_list}`"
            )
            await ctx.send(hint_message)
            return

        # --- Select one random trait per category (excluding Race) ---
        # Filter non-Race traits: if a race is given, restrict by req_race; otherwise allow all
        if race:
            non_race_pool = [
                t for t in traits
                if t.get("category", "").lower() != "race"
                and t.get("req_race", "Any").lower() in ("any", race)
            ]
        else:
            non_race_pool = [
                t for t in traits
                if t.get("category", "").lower() != "race"
            ]

        errors = []
        available_traits = non_race_pool.copy()
        results = []

        # --- Automatically pick a Race trait FIRST — only if race was provided ---
        if race:
            # Priority 1: Race traits with race name in parentheses e.g. "Vandal (Human)"
            race_specific_pool = [
                t for t in traits
                if t.get("category", "").lower() == "race"
                and f"({race})" in t.get("name", "").lower()
            ]
            # Priority 2: fallback to any Race trait
            race_fallback_pool = [
                t for t in traits
                if t.get("category", "").lower() == "race"
                and f"({race})" not in t.get("name", "").lower()
            ]
            race_pool = race_specific_pool if race_specific_pool else race_fallback_pool
            if race_pool:
                results = [random.choice(race_pool)]
            else:
                errors.append(f"race({race})")

        # --- Then select one trait per requested category (Level 6, Level 11, ...) ---
        for req_cat in final_categories:
            pool = [t for t in available_traits if t.get("category", "").lower() == req_cat]
            if pool:
                selected = random.choice(pool)
                results.append(selected)
                available_traits.remove(selected)
            else:
                errors.append(req_cat)

        if not results:
            await ctx.send(
                f"❌ No traits found for category(s) `{', '.join(errors)}` with race `{race}`.\n"
                f"**Available Categories:** `{cat_list}`"
            )
            return

        # --- Build embed ---
        race_desc = f" for race **{race.capitalize()}**" if race else ""
        embed = discord.Embed(
            title="🎲 Random Traits",
            description=f"Traits{race_desc} from your selected categories:",
            color=discord.Color.dark_blue()
        )

        level_labels = ["Level 2", "Level 6", "Level 11"]
        for idx, selected in enumerate(results):
            prefix = level_labels[idx] if idx < len(level_labels) else f"Level {idx + 1}"
            embed.add_field(
                name=f"{prefix} {selected.get('category', 'Unknown')} Trait: {selected.get('name', 'Unknown')}",
                value=f"**[Wiki Page]({selected.get('url', '')})**",
                inline=False
            )

        footer_text = "Mineria RPG • Traits"
        if errors:
            footer_text += f" | Not found: {', '.join(errors)}"

        avatar_url = self.bot.user.avatar.url if (self.bot.user and self.bot.user.avatar) else None
        embed.set_footer(text=footer_text, icon_url=avatar_url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Traits(bot))
