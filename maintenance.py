import discord
from discord.ext import commands, tasks
import shutil
import os
from datetime import datetime, time
import logging
from pathlib import Path

logger = logging.getLogger("MineriaBot")

class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_schedule.start()

    def cog_unload(self):
        self.backup_schedule.cancel()

    @tasks.loop(minutes=1)
    async def backup_schedule(self):
        """Checks every minute to trigger scheduled backups at 08:00."""
        now = datetime.now()
        
        # Schedule: 08:00 AM
        if now.hour == 8 and now.minute == 0:
            # Daily Backup
            await self.perform_backup("daily", retention=7)
            
            # Weekly Backup (Monday = 0)
            if now.weekday() == 0:
                await self.perform_backup("weekly", retention=5)

    @backup_schedule.before_loop
    async def before_schedule(self):
        await self.bot.wait_until_ready()

    def prune_backups(self, directory: Path, limit: int):
        """Keeps only the regular 'limit' number of backups."""
        try:
            files = sorted(directory.glob("*.zip"), key=lambda f: f.stat().st_mtime)
            
            if len(files) > limit:
                for f in files[:-limit]:
                    f.unlink()
                    logger.info(f"🗑️ Pruned old backup: {f.name} from {directory.name}")
        except Exception as e:
            logger.error(f"⚠️ Failed to prune {directory.name}: {e}")

    @commands.command(name="backup", hidden=True)
    @commands.is_owner()
    async def manual_backup(self, ctx):
        """Triggers a immediate manual backup to the daily folder."""
        await ctx.send("⏳ Starting manual backup...")
        try:
            filename = await self.perform_backup("daily", retention=7)
            if filename:
                await ctx.send(f"✅ Backup created in daily: `{filename}`")
            else:
                await ctx.send("❌ Backup failed. Check logs.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    async def perform_backup(self, backup_type: str, retention: int = 7):
        """
        Creates a backup in backups/<backup_type>/
        backup_type: 'daily' or 'weekly'
        retention: number of files to keep
        """
        data_dir = Path("data")
        backup_root = Path("backups")
        target_dir = backup_root / backup_type
        
        if not data_dir.exists():
            logger.warning("⚠️ Data directory not found. Skipping backup.")
            return None

        target_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"mineria_{backup_type}_{timestamp}"
        backup_path = target_dir / backup_filename
        
        try:
            # shutil.make_archive automatically adds .zip extension
            shutil.make_archive(str(backup_path), 'zip', str(data_dir))
            
            final_filename = f"{backup_filename}.zip"
            logger.info(f"✅ {backup_type.capitalize()} backup created: {final_filename}")
            
            self.prune_backups(target_dir, retention)
            return final_filename
        except Exception as e:
            logger.error(f"❌ {backup_type.capitalize()} backup failed: {e}")
            return None

async def setup(bot):
    await bot.add_cog(Maintenance(bot))
