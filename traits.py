import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from pathlib import Path
from typing import Optional, List

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

    async def category_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        cats = sorted(list(set([t.get("category", "") for t in self.traits if t.get("category")])))
        
        # Ensure special choices are present
        if "Race" not in cats:
            cats.append("Race")
        if "Random" not in cats:
            cats.append("Random")

        current_lower = current.lower()
        return [
            app_commands.Choice(name=cat, value=cat)
            for cat in cats if current_lower in cat.lower()
        ][:25]

    @commands.hybrid_command(name="trait", aliases=["t"], description="Displays a random trait for each specified category.")
    @app_commands.describe(
        category1="First category (e.g. Combat, Faith, Social, Magic, Race)",
        category2="Second category",
        category3="Third category",
        category4="Optional fourth category",
        category5="Optional fifth category",
        race="Your race (required if choosing 'Race' category)"
    )
    @app_commands.autocomplete(
        category1=category_autocomplete,
        category2=category_autocomplete,
        category3=category_autocomplete,
        category4=category_autocomplete,
        category5=category_autocomplete
    )
    async def trait(
        self,
        ctx: commands.Context,
        category1: str,
        category2: str,
        category3: str,
        category4: Optional[str] = None,
        category5: Optional[str] = None,
        race: Optional[str] = None
    ):
        """Displays a random trait for each specified category.
        Race specification is only needed if 'Race' category is requested.
        Usage: !trait combat social magic  OR  !trait race(human) combat social
        """
        traits = self.traits.copy()

        if not traits:
            await ctx.send("❌ Trait list not found.")
            return

        raw_args = [category1, category2, category3]
        if category4:
            raw_args.append(category4)
        if category5:
            raw_args.append(category5)

        # --- Parse arguments and build selection order ---
        # Get the race from arguments or explicit race param
        parsed_race = race
        if not parsed_race:
            for arg in raw_args:
                arg_lower = arg.lower().strip()
                if arg_lower.startswith("race(") and arg_lower.endswith(")"):
                    parsed_race = arg_lower[5:-1].strip()
                    break

        selection_order = []  # List of tuples: ('category', cat_name) or ('race', race_name)
        for arg in raw_args:
            arg_lower = arg.lower().strip()
            if arg_lower.startswith("race(") and arg_lower.endswith(")"):
                r_name = arg_lower[5:-1].strip()
                selection_order.append(('race', r_name))
            elif arg_lower == "race":
                selection_order.append(('race', parsed_race))
            elif arg_lower == "random":
                selection_order.append(('random', None))
            else:
                selection_order.append(('category', arg_lower))

        all_cats = sorted(list(set([t.get("category", "") for t in traits if t.get("category")])))
        display_cats = [cat if cat != "Race" else "Race(human)" for cat in all_cats]
        cat_list = ", ".join(display_cats)

        # Determine if user requested a Race category
        wants_race_trait = any(t == 'race' for t, _ in selection_order) or (parsed_race is not None)

        if wants_race_trait and not parsed_race:
            hint_message = (
                f"❌ You must specify a race when requesting a Race trait.\n"
                f"**Usage:** `/trait category1: Race category2: Combat category3: Social race: Human` or `!trait race(human) combat social`\n"
                f"**Available Categories:** `{cat_list}`"
            )
            await ctx.send(hint_message)
            return

        # --- Enforce at least 3 different categories ---
        unique_selections = set()
        for t, val in selection_order:
            if t == 'category':
                unique_selections.add(val.lower())
            elif t == 'race':
                unique_selections.add('race')
            elif t == 'random':
                unique_selections.add(f"random_{len(unique_selections)}")
                
        if len(unique_selections) < 3:
            hint_message = (
                f"❌ You must specify at least 3 different categories.\n"
                f"**Usage:** `/trait category1: Combat category2: Social category3: Magic` or `!trait combat social magic`\n"
                f"**Available Categories:** `{cat_list}`"
            )
            await ctx.send(hint_message)
            return

        # --- Select one random trait per category (excluding Race) ---
        # Filter non-Race traits: if a race is given, restrict by req_race; otherwise allow all
        if parsed_race:
            non_race_pool = [
                t for t in traits
                if t.get("category", "").lower() != "race"
                and t.get("req_race", "Any").lower() in ("any", parsed_race.lower())
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
                used_categories.append(val.lower())
            elif t == 'race':
                resolved_order.append((t, val))
            elif t == 'random':
                available = [c for c in all_cats if c.lower() != "race" and c.lower() not in used_categories]
                if available:
                    picked = random.choice(available)
                    resolved_order.append(('category', picked))
                    used_categories.append(picked.lower())
                else:
                    errors.append("random")

        # Select traits in the exact resolved order
        for t, val in resolved_order:
            if t == 'category':
                pool = [tr for tr in available_traits if tr.get("category", "").lower() == val.lower()]
                if pool:
                    selected = random.choice(pool)
                    results.append(selected)
                    available_traits.remove(selected)
                else:
                    errors.append(val)
            elif t == 'race':
                if parsed_race:
                    # Priority 1: Race traits with race name in parentheses e.g. "Vandal (Human)"
                    race_specific_pool = [
                        tr for tr in traits
                        if tr.get("category", "").lower() == "race"
                        and f"({parsed_race.lower()})" in tr.get("name", "").lower()
                    ]
                    # Priority 2: fallback to any Race trait
                    race_fallback_pool = [
                        tr for tr in traits
                        if tr.get("category", "").lower() == "race"
                        and f"({parsed_race.lower()})" not in tr.get("name", "").lower()
                    ]
                    race_pool = race_specific_pool if race_specific_pool else race_fallback_pool
                    if race_pool:
                        selected = random.choice(race_pool)
                        results.append(selected)
                    else:
                        errors.append(f"race({parsed_race})")
                else:
                    errors.append("race")

        if not results:
            await ctx.send(
                f"❌ No traits found for category(s) `{', '.join(errors)}` with race `{parsed_race}`.\n"
                f"**Available Categories:** `{cat_list}`"
            )
            return

        # --- Build embed ---
        race_desc = f" for race **{parsed_race.capitalize()}**" if parsed_race else ""
        embed = discord.Embed(
            title="🎲 Random Traits",
            description=f"Traits{race_desc} from your selected categories:",
            color=discord.Color.dark_blue()
        )

        level_labels = ["Üye", "Kıdemli", "Uzman"]
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
