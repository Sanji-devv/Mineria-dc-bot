import os
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("MineriaBot")

load_dotenv()
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
        for ext in ["dice", "character", "help"]:
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