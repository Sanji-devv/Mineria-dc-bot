import discord
from discord.ext import commands
from datetime import datetime, timezone

ACCENT = discord.Color.from_rgb(255, 170, 0)

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["m", "mineria", "h"])
    async def help_command(self, ctx: commands.Context):
        """Displays the modern and clean help menu."""
        bot_avatar = ctx.bot.user.avatar.url if ctx.bot.user.avatar else None

        embed = discord.Embed(
            title="✨ Mineria System Terminal",
            description=(
                "Welcome to the **Mineria Campaign Assistant**.\n"
                "Below are all available commands divided into 3 main categories.\n\n"
                "**Prefix:** `!`  •  **Shortcuts:** `!m`, `!h`, `!mineria`\n"
            ),
            color=ACCENT,
            timestamp=datetime.now(timezone.utc),
        )

        if ctx.author.avatar:
            embed.set_thumbnail(url=ctx.author.avatar.url)

        # --- Part 1: Core Commands ---
        embed.add_field(
            name="🔰 **CORE COMMANDS**",
            value=(
                "> **`!roll <expr>`** ➔ Advanced dice rolling engine. *(e.g., 1d20+7)*\n"
                "> **`!trait <category>`** ➔ Draws a random trait from the specified category.\n"
                "> **`!drawback`** ➔ Suggests a random drawback for your character."
            ),
            inline=False,
        )

        # --- Part 2: Character System ---
        embed.add_field(
            name="👤 **CHARACTER SYSTEM**",
            value=(
                "> **`!char create <race>`** ➔ Starts a new character creation wizard.\n"
                "> **`!char dr <stats>`** ➔ Distributes your rolled stats to your character.\n"
                "> **`!char save <name>`** ➔ Finalizes and saves your character to the system.\n"
                "> **`!char list`** ➔ Lists all your registered characters.\n"
                "> **`!char info [name]`** ➔ Displays the detailed character sheet.\n"
                "> **`!char edit` / `rename` / `delete`** ➔ Character management operations.\n"
                "> **`!xp <name>`** ➔ Checks current XP and level of your character.\n"
                "> **`!kia`** & **`!mia`** ➔ Calculates current XP in case of death or missing-in-action."
            ),
            inline=False,
        )

        # --- Part 3: Utility Commands ---
        embed.add_field(
            name="🛠️ **UTILITY COMMANDS**",
            value=(
                "> **`!wiki`** ➔ Official Mineria universe Wiki and reference pages.\n"
                "> **`!doc`** ➔ Access to server forms and necessary documents.\n"
                "> **`!d`** ➔ Server rank rule check (1 Ranked + 1 Clerk).\n"
                "> **`!rec`** ➔ Toggles the class recommendation system on or off."
            ),
            inline=False,
        )
        
        embed.set_footer(
            text=f"Requested by: {ctx.author.display_name} • Mineria OS",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else bot_avatar,
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))