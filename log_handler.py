import logging
import discord
from discord.ext import commands
from pathlib import Path

# Setup global logger
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("MineriaBot")
    logger.setLevel(logging.INFO)
    
    # Prevent adding multiple handlers if function is called multiple times
    if not logger.handlers:
        # File Handler
        file_handler = logging.FileHandler(log_dir / "mineria.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(file_handler)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(console_handler)
    
    return logger

# Initialize logger immediately so it can be imported
logger = setup_logging()

class LogHandler(commands.Cog, name="LogHandler"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Log when a command is received."""
        logger.info(f"📥 COMMAND REQUEST | User: {ctx.author} ({ctx.author.id}) | Command: {ctx.message.content} | Guild: {ctx.guild}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Log when a command completes successfully."""
        logger.info(f"✅ COMMAND SUCCESS | User: {ctx.author} ({ctx.author.id}) | Command: {ctx.command.name}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Log command errors (user-facing messages handled by error_handler.py)."""
        user_info = f"User: {ctx.author} ({ctx.author.id})"
        cmd_name = ctx.command.name if ctx.command else "Unknown"

        if isinstance(error, commands.CommandNotFound):
            logger.warning(f"🚫 UNKNOWN COMMAND | {user_info} | Message: {ctx.message.content}")
        elif isinstance(error, commands.MissingRequiredArgument):
            logger.warning(f"⚠️ MISSING ARGUMENT | {user_info} | Command: {cmd_name} | Error: {error}")
        elif isinstance(error, commands.BadArgument):
            logger.warning(f"⚠️ BAD ARGUMENT | {user_info} | Command: {cmd_name} | Error: {error}")
        elif isinstance(error, commands.CommandOnCooldown):
            logger.warning(f"⏳ COOLDOWN | {user_info} | Command: {cmd_name} | Retry: {error.retry_after:.2f}s")
        else:
            logger.error(f"❌ COMMAND ERROR | {user_info} | Command: {cmd_name} | Error: {error}", exc_info=True)

async def setup(bot):
    await bot.add_cog(LogHandler(bot))
