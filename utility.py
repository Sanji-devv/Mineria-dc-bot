import discord
from discord.ext import commands
import csv
import io
import aiohttp
from typing import Tuple, List, Dict, Any

# =================================================================================================
# CONSTANTS
# =================================================================================================

# XP & Player Tracking Sheet
XP_SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKwtaT_9FOnwiCk5BtCKFJSslYUFdspL0R03AMM34vI/export?format=csv&gid=1293793215"

# =================================================================================================
# UTILITY COG  (XP & duplicate-player check)
# =================================================================================================

class OneTimeCommands(commands.Cog):
    """XP table queries and duplicate player detection."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── XP sheet fetcher ─────────────────────────────────────────────────────

    async def fetch_xp_data(self) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetches and parses the XP Google Sheet data.

        Returns:
            Tuple: (List of character dicts, Count of skipped/invalid rows)

        Sheet columns assumed:
          B (1) = Character Name
          C (2) = Player Name
          D (3) = XP
          E (4) = Rank
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(XP_SHEET_URL) as resp:
                if resp.status != 200:
                    return [], 0
                content = await resp.text()

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return [], 0

        skipped_count = 0
        parsed = []

        for row in rows[1:]:  # Skip header
            if len(row) < 5:
                skipped_count += 1
                continue

            char_name   = row[1].strip()
            player_name = row[2].strip()
            xp          = row[3].strip()
            rank        = row[4].strip()

            if not player_name or not char_name:
                skipped_count += 1
                continue

            parsed.append({
                "char_name":   char_name,
                "player_name": player_name,
                "xp":          xp,
                "rank":        rank,
            })

        return parsed, skipped_count

    # ── Duplicate check command ───────────────────────────────────────────────

    @commands.command(name="d", aliases=["dup", "checkdup"])
    async def duplicate_check_command(self, ctx: commands.Context):
        """
        Scans the Google Sheet for players violating character limit rules.

        Rules:
        - A player can have at most 2 characters.
        - If they have 2, one MUST be a Clerk and the other Ranked.
        - 2 Ranked, 2 Clerks, or 3+ characters is a violation.
        - Inactive characters are ignored.
        """
        msg = await ctx.send("🔄 Fetching XP table data...")
        data, skipped = await self.fetch_xp_data()

        # Step 1: Filter Active vs Inactive
        active_chars = []
        inactive_count = 0
        inactive_keywords = ["inactive", "dead", "left", "leave"]

        for entry in data:
            rank_str = entry["rank"].lower()
            if any(k in rank_str for k in inactive_keywords):
                inactive_count += 1
            else:
                active_chars.append(entry)

        # Step 2: Group by Player
        players: Dict[str, list] = {}
        for entry in active_chars:
            p = entry["player_name"]
            if p not in players:
                players[p] = []
            players[p].append(entry)

        # Step 3: Analyze Violations
        violations: Dict[str, list] = {}

        for player, chars in players.items():
            if len(chars) <= 1:
                continue

            clerk_count  = 0
            ranked_count = 0

            for c in chars:
                r_lower = c['rank'].lower()
                if "clerk" in r_lower:
                    clerk_count += 1
                else:
                    ranked_count += 1

            is_valid_duo = (len(chars) == 2 and ranked_count == 1 and clerk_count == 1)
            if not is_valid_duo:
                violations[player] = chars

        await msg.delete()

        # Step 4: Build Rich Embed
        has_violations = bool(violations)
        embed = discord.Embed(
            title="🔍 Duplicate Player Check",
            color=discord.Color.red() if has_violations else discord.Color.green()
        )

        embed.add_field(
            name="📊 Scan Summary",
            value=(
                f"📋 Scanned: **{len(data)}** entries\n"
                f"🟢 Active:   **{len(active_chars)}** characters\n"
                f"🛌 Inactive: **{inactive_count}** (ignored)\n"
                f"⚠️  Skipped:  **{skipped}** rows (missing data)"
            ),
            inline=True
        )

        if has_violations:
            embed.add_field(
                name="🚨 Status",
                value=f"**{len(violations)}** player(s) in violation",
                inline=True
            )
        else:
            embed.add_field(
                name="✅ Status",
                value="All active players are **compliant**!",
                inline=True
            )

        embed.add_field(
            name="📜 Allowed Rule",
            value="Max **1 Ranked** + **1 Clerk** per player",
            inline=False
        )

        if has_violations:
            embed.add_field(name="\u200b", value="─" * 30, inline=False)
            for player, chars in violations.items():
                char_lines = []
                for c in chars:
                    r_lower  = c['rank'].lower()
                    is_clerk = "clerk" in r_lower
                    role_tag = "🟡 Clerk" if is_clerk else "🔴 Ranked"
                    char_lines.append(f"{role_tag} **{c['char_name']}** — *{c['rank']}*")
                embed.add_field(
                    name=f"🚧 {player} ({len(chars)} characters)",
                    value="\n".join(char_lines),
                    inline=False
                )
        else:
            embed.add_field(
                name="✅ Result",
                value="No violations found. The server is clean! 🎉",
                inline=False
            )

        embed.set_footer(text="Mineria RPG • Rule Enforcement", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)
    @commands.command(name="drawback", aliases=["drawbacks"])
    async def drawback_command(self, ctx: commands.Context):
        """Sends the Pathfinder drawbacks link."""
        embed = discord.Embed(
            title="Pathfinder Drawbacks",
            description="You can find the list of Pathfinder Drawbacks here:\n\n[Click here for Drawbacks](https://www.d20pfsrd.com/traits/drawbacks/)",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Mineria RPG • Drawbacks", icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(OneTimeCommands(bot))