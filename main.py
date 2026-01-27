import os
import asyncio
import discord
from discord.ext import commands
from pathlib import Path
from dotenv import load_dotenv
from log_handler import logger

load_dotenv(Path(__file__).parent / ".env")

# Token and Prefix Logic
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIXES = ["!mineria ", "!m ", "!"]

if TOKEN:
    logger.info("🚀 Using Production Token")
else:
    logger.warning("⚠️ No DISCORD_TOKEN found in environment variables")

class MineriaBot(commands.Bot):
    def __init__(self, command_prefix):
        intents = discord.Intents.default()
        intents.message_content = intents.members = True
        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def setup_hook(self):
        extensions = ["character", "dice", "help", "maintenance", "log_handler", "links", "documents", "utility"]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"✅ Loaded extension: {ext}")
            except Exception as e:
                logger.critical(f"❌ Failed to load extension {ext}: {e}")

    async def on_ready(self):
        logger.info(f"✨ {self.user.name} is online! servers: {len(self.guilds)}")

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ ERROR: DISCORD_TOKEN not found in .env file.")
    else:
        bot = MineriaBot(PREFIXES)
        bot.run(TOKEN)