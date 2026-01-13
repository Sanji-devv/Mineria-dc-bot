import discord
from discord.ext import commands, tasks
import shutil
import os
from datetime import datetime
import logging

logger = logging.getLogger("MineriaBot")

class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_task.start()

    def cog_unload(self):
        self.backup_task.cancel()

    @tasks.loop(hours=24)
    async def backup_task(self):
        """Creates a periodic backup of the data directory."""
        await self.bot.wait_until_ready()
        await self.perform_backup()

    def prune_backups(self, backup_dir):
        """Keeps only the last 7 backups."""
        try:
            files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith('.zip')]
            files.sort(key=os.path.getmtime)
            
            if len(files) > 7:
                for f in files[:-7]:
                    os.remove(f)
                    logger.info(f"🗑️ Removed old backup: {os.path.basename(f)}")
        except Exception as e:
            logger.error(f"⚠️ Failed to prune old backups: {e}")

    @backup_task.before_loop
    async def before_backup(self):
        await self.bot.wait_until_ready()

    @commands.command(name="backup", hidden=True)
    @commands.is_owner()
    async def manual_backup(self, ctx):
        """Triggers a manual backup (Owner only)."""
        await ctx.send("⏳ Starting manual backup...")
        try:
            # Re-use logic or just call the function if refactored, 
            # but for now I'll just copy the core logic or better, refactor.
            # actually better to refactor backup_task to call a method.
            filename = await self.perform_backup()
            if filename:
                await ctx.send(f"✅ Backup created: `{filename}`")
            else:
                await ctx.send("❌ Backup failed. Check logs.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    async def perform_backup(self):
        """Core backup logic."""
        data_dir = "data"
        backup_dir = "backups"
        
        if not os.path.exists(data_dir):
            logger.warning("⚠️ Data directory not found. Skipping backup.")
            return None

        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"mineria_backup_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            shutil.make_archive(backup_path, 'zip', data_dir)
            logger.info(f"✅ Backup created successfully: {backup_filename}.zip")
            self.prune_backups(backup_dir)
            return f"{backup_filename}.zip"
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None


async def setup(bot):
    await bot.add_cog(Maintenance(bot))
