import discord
from discord.ext import commands
from pathlib import Path
import difflib

class Documents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.files_dir = Path("files")
        self.files_dir.mkdir(exist_ok=True)

    @commands.command(name="doc")
    async def doc_command(self, ctx, *, query: str = None):
        """Lists files or downloads a specific document."""
        
        # Get all files naturally sorted
        files = [f for f in self.files_dir.iterdir() if f.is_file()]
        
        if not files:
            await ctx.send("📂 The `files/` directory is currently empty.")
            return

        # 1. List Mode
        if not query:
            embed = discord.Embed(
                title="📂 Available Documents",
                description="Use `!doc <name>` to download a file.",
                color=discord.Color.gold()
            )
            
            file_list = []
            for file in files:
                size_mb = file.stat().st_size / (1024 * 1024)
                file_list.append(f"📄 **{file.name}** ({size_mb:.2f} MB)")
            
            embed.add_field(name="Files", value="\n".join(file_list) or "No files.", inline=False)
            embed.set_footer(text="Mineria RPG • Documents", icon_url=self.bot.user.avatar.url)
            await ctx.send(embed=embed)
            return

        # 2. Download Mode (Fuzzy Search)
        # Try exact match first
        target_file = self.files_dir / query
        
        if not target_file.exists():
            # Try searching by name (case insensitive)
            file_names = [f.name for f in files]
            matches = difflib.get_close_matches(query, file_names, n=1, cutoff=0.5)
            
            if matches:
                 target_file = self.files_dir / matches[0]
            else:
                await ctx.send(f"❌ File **{query}** not found.")
                return

        # Check total size limit for Discord (8MB for non-nitro, safer to warn if huge)
        # We'll just try to send it.
        try:
            await ctx.send(f"sw Downloading **{target_file.name}**...", file=discord.File(target_file))
        except discord.HTTPException:
            await ctx.send("❌ File is too large to upload directly to Discord (Limit: 8MB/50MB).")
        except Exception as e:
            await ctx.send(f"❌ Error uploading file: {e}")

async def setup(bot):
    await bot.add_cog(Documents(bot))
