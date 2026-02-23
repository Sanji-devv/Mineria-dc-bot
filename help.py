import discord
from discord.ext import commands
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
#  HELP COG  —  Single rich embed, all commands visible at once
# ══════════════════════════════════════════════════════════════

ACCENT = discord.Color.from_rgb(88, 101, 242)   # Discord blurple

# Thin visual separator that fits inside a Discord field
DIV = "┄" * 28


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["m", "mineria", "h"])
    async def help_command(self, ctx: commands.Context):
        """Shows the full command manual."""

        bot_avatar = ctx.bot.user.avatar.url if ctx.bot.user.avatar else None

        embed = discord.Embed(
            description=(
                "### 🏰  Mineria Campaign Bot\n"
                "> *Pathfinder 1e tabletop assistant*\n"
                f"> Prefix **`!`**  •  shortcuts `!m` `!h` `!mineria`"
            ),
            color=ACCENT,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(name="📖  Command Manual", icon_url=bot_avatar)
        if ctx.author.avatar:
            embed.set_thumbnail(url=ctx.author.avatar.url)

        # ── 🎲 Dice & Loot ────────────────────────────────────
        embed.add_field(
            name="🎲  Dice & Loot",
            value=(
                f"`!roll <expr>` — dice roller\n"
                f"  ↳ `4d6k3`  `2d20+5`  `d6, d8`\n"
                f"`!loot generate <CR> [n]` — loot drop\n"
                f"  ↳ coin reward + bonus consumable\n"
                f"`!wiki` — Pathfinder reference links\n"
                f"{DIV}"
            ),
            inline=False,
        )

        # ── 🛒 Item Market ─────────────────────────────────────
        embed.add_field(
            name="🛒  Item Market",
            value=(
                f"`!item listdown <price|AC|name>` — exp → cheap\n"
                f"`!item listup  <price|AC|name>` — cheap → exp\n"
                f"`!item info <name>` — full stats + wiki link\n"
                f"`!item filter <rarity> [stat]` — combined filter\n"
                f"  ↳ `common` `uncommon` `rare` `epic` `legendary`\n"
                f"  ↳ `STR` `DEX` `CON` `INT` `WIS` `CHA`\n"
                f"`!spell <name>` — SRD spell search\n"
                f"{DIV}"
            ),
            inline=False,
        )

        # ── 🛠️ Tools (left) + ✨ Char (right) ──────────────
        embed.add_field(
            name="🛠️  Registry & Tools",
            value=(
                f"`!d` — duplicate player scan\n"
                f"  ↳ *(1 Ranked + 1 Clerk rule)*\n"
                f"`!doc [name]` — session files\n"
            ),
            inline=True,
        )

        embed.add_field(
            name="✨  Character",
            value=(
                f"`!char help` — full character command list\n"
                f"`!rec [open|close]` — class recommendations\n"
            ),
            inline=True,
        )

        embed.add_field(name="\u200b", value="\u200b", inline=True)  # spacer

        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}  •  Mineria RPG",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else bot_avatar,
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))