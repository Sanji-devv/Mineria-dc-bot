import discord
from discord.ext import commands
from discord import app_commands
from pathlib import Path
import difflib
from typing import Optional, List

class Documents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.docs_dir = Path("mineria_files/docs")
        self.maps_dir = Path("mineria_files/maps")
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.maps_dir.mkdir(parents=True, exist_ok=True)

    async def doc_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not self.docs_dir.exists():
            return []
        files = [f.name for f in self.docs_dir.iterdir() if f.is_file()]
        current_lower = current.lower()
        matches = [f for f in files if current_lower in f.lower()]
        return [
            app_commands.Choice(name=f, value=f)
            for f in sorted(matches, key=lambda x: x.lower())
        ][:25]

    async def map_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not self.maps_dir.exists():
            return []
        files = [f.stem for f in self.maps_dir.iterdir() if f.is_file()]
        current_lower = current.lower()
        matches = [f for f in files if current_lower in f.lower()]
        return [
            app_commands.Choice(name=f, value=f)
            for f in sorted(matches, key=lambda x: x.lower())
        ][:25]

    # ─────────────────────────────────────────────
    #  !doc  –  list or download a document
    # ─────────────────────────────────────────────
    @commands.hybrid_command(name="doc", description="Lists all downloadable files, or downloads one by name.")
    @app_commands.describe(query="The document name to download (autocomplete list). Leave empty to list all.")
    @app_commands.autocomplete(query=doc_autocomplete)
    async def doc_command(self, ctx: commands.Context, *, query: Optional[str] = None):
        """Lists all downloadable files, or downloads one by name."""
        # Bare `!doc` or `!doc list` → show list
        if not query or query.lower().strip() == "list":
            await self._list_docs(ctx)
            return

        # Otherwise treat query as a filename to download
        await self._send_doc(ctx, query)

    async def _list_docs(self, ctx):
        files = [f for f in self.docs_dir.iterdir() if f.is_file()]
        if not files:
            await ctx.send("📂 The `mineria_files/docs/` directory is currently empty.")
            return

        embed = discord.Embed(
            title="📂 Available Documents",
            description="Use `!doc <name>` to download a file.",
            color=discord.Color.gold()
        )
        file_list = []
        for f in sorted(files, key=lambda x: x.name.lower()):
            size_mb = f.stat().st_size / (1024 * 1024)
            file_list.append(f"📄 **{f.name}** ({size_mb:.2f} MB)")
        embed.add_field(name=f"Files ({len(files)})", value="\n".join(file_list) or "No files.", inline=False)
        
        avatar_url = self.bot.user.avatar.url if (self.bot.user and self.bot.user.avatar) else None
        embed.set_footer(text="Mineria RPG • Documents", icon_url=avatar_url)
        await ctx.send(embed=embed)

    async def _send_doc(self, ctx, query: str):
        files = [f for f in self.docs_dir.iterdir() if f.is_file()]
        if not files:
            await ctx.send("📂 The `mineria_files/docs/` directory is currently empty.")
            return

        target_file = self.docs_dir / query
        if not target_file.exists():
            file_names = [f.name for f in files]
            matches = difflib.get_close_matches(query, file_names, n=1, cutoff=0.5)
            if matches:
                target_file = self.docs_dir / matches[0]
            else:
                await ctx.send(
                    f"❌ File **{query}** not found.\n"
                    "Use `!doc` or `/doc` to see all available files."
                )
                return

        # Defer interaction if we are handling slash command to prevent timeout
        if ctx.interaction:
            await ctx.interaction.response.defer()

        try:
            await ctx.send(f"📥 Downloading **{target_file.name}**...", file=discord.File(target_file))
        except discord.HTTPException:
            await ctx.send("❌ File is too large to upload directly to Discord (Limit: 8 MB / 50 MB).")
        except Exception as e:
            await ctx.send(f"❌ Error uploading file: {e}")

    # ─────────────────────────────────────────────
    #  !map  –  list maps or send one by name
    # ─────────────────────────────────────────────
    @commands.hybrid_command(name="map", description="Lists all maps, or displays one by name.")
    @app_commands.describe(name="The map name to display (autocomplete list). Leave empty to list all.")
    @app_commands.autocomplete(name=map_autocomplete)
    async def map_command(self, ctx: commands.Context, *, name: Optional[str] = None):
        """Lists all maps, or displays one by name."""
        if not name or name.lower().strip() == "list":
            await self._list_maps(ctx)
        else:
            await self._send_map(ctx, name)

    async def _list_maps(self, ctx):
        maps = [f for f in self.maps_dir.iterdir() if f.is_file()]
        if not maps:
            await ctx.send("🗺️ The `mineria_files/maps/` directory is currently empty.")
            return

        embed = discord.Embed(
            title="🗺️ Available Maps",
            description="Use `!map <name>` to display a map.",
            color=discord.Color.blue()
        )
        map_list = [f"🖼️ **{f.stem}**" for f in sorted(maps, key=lambda x: x.stem.lower())]
        embed.add_field(name=f"Maps ({len(maps)})", value="\n".join(map_list), inline=False)
        
        avatar_url = self.bot.user.avatar.url if (self.bot.user and self.bot.user.avatar) else None
        embed.set_footer(text="Mineria RPG • Maps", icon_url=avatar_url)
        await ctx.send(embed=embed)

    async def _send_map(self, ctx, name: str):
        """Find and send a map image by name (fuzzy match)."""
        maps = [f for f in self.maps_dir.iterdir() if f.is_file()]
        if not maps:
            await ctx.send("🗺️ No maps found in `mineria_files/maps/`.")
            return

        match = next((f for f in maps if f.stem.lower() == name.lower()), None)

        if not match:
            stems = [f.stem for f in maps]
            fuzzy = difflib.get_close_matches(name, stems, n=1, cutoff=0.4)
            if fuzzy:
                match = next(f for f in maps if f.stem == fuzzy[0])
            else:
                await ctx.send(
                    f"❌ Map **{name}** not found. "
                    "Use `!map` or `/map` to see all available maps."
                )
                return

        # Defer interaction if we are handling slash command to prevent timeout
        if ctx.interaction:
            await ctx.interaction.response.defer()

        try:
            await ctx.send(f"🗺️ **{match.stem}**", file=discord.File(match))
        except discord.HTTPException:
            await ctx.send("❌ Map file is too large to upload directly to Discord.")
        except Exception as e:
            await ctx.send(f"❌ Error uploading map: {e}")

async def setup(bot):
    await bot.add_cog(Documents(bot))
