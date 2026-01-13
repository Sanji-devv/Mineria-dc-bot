import os
import asyncio
import logging
import discord
from discord.ext import commands
from pathlib import Path
from dotenv import load_dotenv

# Setup Logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger = logging.getLogger("MineriaBot")
logger.setLevel(logging.INFO)

# File Handler
file_handler = logging.FileHandler(log_dir / "mineria.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(file_handler)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(console_handler)

load_dotenv(Path(__file__).parent / ".env")
TOKEN = os.getenv("DISCORD_TOKEN")

class MineriaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = intents.members = True
        super().__init__(
            command_prefix=["!", "!mineria ", "!m "],
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def setup_hook(self):
        """Load extensions on startup."""
        for ext in ["dice", "character", "help", "maintenance"]:
            try:
                await self.load_extension(ext)
                logger.info(f"✅ Loaded extension: {ext}")
            except Exception as e:
                logger.error(f"❌ Failed to load extension {ext}: {e}")

    async def on_ready(self):
        logger.info(f"✨ {self.user.name} is online! servers: {len(self.guilds)}")

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ ERROR: DISCORD_TOKEN not found in .env file.")
    else:
        bot = MineriaBot()
        bot.run(TOKEN)