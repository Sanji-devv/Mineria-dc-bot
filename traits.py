import discord
from discord.ext import commands
import json
import random
from pathlib import Path

class Traits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.traits = []

    async def cog_load(self):
        """Loads traits database asynchronously via executor."""
        import asyncio
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._load_traits_sync)
        except Exception as e:
            print(f"Error preloading traits: {e}")

    def _load_traits_sync(self):
        file_path = Path(__file__).parent / "datas" / "traits.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.traits = data.get("traits", [])

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

        # --- Parse arguments and build selection order ---
        selection_order = []  # List of tuples: ('category', cat_name) or ('race', race_name)
        
        # Pre-pass to get the race (needed for filtering pools)
        race = None
        for arg in args:
            arg_lower = arg.lower().strip()
            if arg_lower.startswith("race(") and arg_lower.endswith(")"):
                race = arg_lower[5:-1].strip()
                break

        # Second pass: build the selection order
        i = 0
        while i < len(args):
            arg = args[i]
            arg_lower = arg.lower().strip()
            if arg_lower.startswith("race(") and arg_lower.endswith(")"):
                r_name = arg_lower[5:-1].strip()
                selection_order.append(('race', r_name))
            elif arg_lower == "random":
                count = 1
                if i + 1 < len(args) and args[i + 1].isdigit():
                    count = int(args[i + 1])
                    i += 1
                for _ in range(count):
                    selection_order.append(('random', None))
            else:
                if arg_lower == "race":
                    selection_order.append(('race', race))
                else:
                    selection_order.append(('category', arg_lower))
            i += 1

        all_cats = sorted(list(set([t.get("category", "") for t in traits if t.get("category")])))
        # Show Race as Race(human) in category hint
        display_cats = [cat if cat != "Race" else "Race(human)" for cat in all_cats]
        cat_list = ", ".join(display_cats)

        # Determine if user requested a Race category
        wants_race_trait = any(t == 'race' for t, _ in selection_order) or (race is not None)

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

        # --- Enforce at least 3 different categories ---
        unique_selections = set()
        for t, val in selection_order:
            if t == 'category':
                unique_selections.add(val)
            elif t == 'race':
                unique_selections.add('race')
            elif t == 'random':
                unique_selections.add(f"random_{len(unique_selections)}")
                
        if len(unique_selections) < 3:
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

        # Resolve 'random' to concrete categories
        resolved_order = []
        used_categories = []
        for t, val in selection_order:
            if t == 'category':
                resolved_order.append((t, val))
                used_categories.append(val)
            elif t == 'race':
                resolved_order.append((t, val))
            elif t == 'random':
                available = [c.lower() for c in all_cats if c.lower() != "race" and c.lower() not in used_categories]
                if available:
                    picked = random.choice(available)
                    resolved_order.append(('category', picked))
                    used_categories.append(picked)
                else:
                    errors.append("random")

        # Select traits in the exact resolved order
        for t, val in resolved_order:
            if t == 'category':
                pool = [tr for tr in available_traits if tr.get("category", "").lower() == val]
                if pool:
                    selected = random.choice(pool)
                    results.append(selected)
                    available_traits.remove(selected)
                else:
                    errors.append(val)
            elif t == 'race':
                if race:
                    # Priority 1: Race traits with race name in parentheses e.g. "Vandal (Human)"
                    race_specific_pool = [
                        tr for tr in traits
                        if tr.get("category", "").lower() == "race"
                        and f"({race})" in tr.get("name", "").lower()
                    ]
                    # Priority 2: fallback to any Race trait
                    race_fallback_pool = [
                        tr for tr in traits
                        if tr.get("category", "").lower() == "race"
                        and f"({race})" not in tr.get("name", "").lower()
                    ]
                    race_pool = race_specific_pool if race_specific_pool else race_fallback_pool
                    if race_pool:
                        selected = random.choice(race_pool)
                        results.append(selected)
                    else:
                        errors.append(f"race({race})")
                else:
                    errors.append("race")

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
            cat = selected.get('category', 'Unknown')
            name = selected.get('name', 'Unknown')
            url = selected.get('url', '')
            
            prefix = level_labels[idx] if idx < len(level_labels) else f"Level {idx + 1}"
            
            if cat.lower() == 'race':
                field_name = f"{prefix} Race Trait: {name}"
            else:
                field_name = f"{prefix} {cat} Trait: {name}"
                
            embed.add_field(
                name=field_name,
                value=f"**[Wiki Page]({url})**",
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
