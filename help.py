import discord
from discord.ext import commands
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
#  HELP COG  —  Split into multiple embeds for size limits
# ══════════════════════════════════════════════════════════════

ACCENT = discord.Color.from_rgb(88, 101, 242)   # Discord blurple
DIV = "┄" * 28


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["m", "mineria", "h"])
    async def help_command(self, ctx: commands.Context):
        """Shows the full command manual in two parts."""

        bot_avatar = ctx.bot.user.avatar.url if ctx.bot.user.avatar else None

        # ── PART 1: Core Mechanics ────────────────────────────────────
        embed1 = discord.Embed(
            description=(
                "### 🏰  Mineria Campaign Bot (Part 1)\n"
                "> *Pathfinder 1e tabletop assistant*\n"
                f"> Prefix **`!`**  •  shortcuts `!m` `!h` `!mineria`"
            ),
            color=ACCENT,
        )
        embed1.set_author(name="📖  Command Manual", icon_url=bot_avatar)
        if ctx.author.avatar:
            embed1.set_thumbnail(url=ctx.author.avatar.url)

        embed1.add_field(
            name="🎲  Dice & Loot",
            value=(
                f"`!roll <expr>` — dice roller (`1d8+3d6`, `4d6k3`)\n"
                f"`!loot generate <CR> [n]` — loot drop generator\n"
                f"{DIV}"
            ),
            inline=False,
        )

        embed1.add_field(
            name="🛒  Item Market",
            value=(
                f"`!item info <name>` — full item stats & variants\n"
                f"`!item search <txt>` — search name & description\n"
                f"`!item listdown <gold|AC|name>` — sort high → low\n"
                f"`!item listup <gold|AC|name>` — sort low → high\n"
                f"`!item filter <rarity> [stat]` — rarity/stat filter\n"
                f"`!item slot <slot>` — items by equipment slot\n"
                f"`!item stat <stat>` — items boosting a stat\n"
                f"{DIV}"
            ),
            inline=False,
        )

        embed1.add_field(
            name="✨  Spells & Links",
            value=(
                f"`!spell <name>` — Pathfinder spell search\n"
                f"`!wiki` — Pathfinder reference links\n"
                f"`!drawback` — Pathfinder drawbacks link\n"
            ),
            inline=False,
        )

        # ── PART 2: Character, Tools, Admin ───────────────────────────
        embed2 = discord.Embed(
            description=(
                "### ⚙️  Mineria Campaign Bot (Part 2)\n"
                "> *Continued command manual*"
            ),
            color=ACCENT,
            timestamp=datetime.now(timezone.utc),
        )

        embed2.add_field(
            name="👤  Character & Inventory",
            value=(
                f"`!char help` — full character command list\n"
                f"`!rec [open|close]` — class recommendations\n"
                f"{DIV}"
            ),
            inline=False,
        )

        embed2.add_field(
            name="🛠️  Registry & Tools",
            value=(
                f"`!d` — duplicate player scan (1 Ranked + 1 Clerk)\n"
                f"`!doc [name]` — session files & registry\n"
                f"{DIV}"
            ),
            inline=False,
        )



        embed2.set_footer(
            text=f"Requested by {ctx.author.display_name}  •  Mineria RPG",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else bot_avatar,
        )

        await ctx.send(embed=embed1)
        await ctx.send(embed=embed2)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))