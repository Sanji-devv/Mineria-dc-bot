import discord
from discord.ext import commands
from log_handler import logger
import traceback

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global Error Handler"""
        
        # Ignored errors (e.g. CommandNotFound is noisy)
        if isinstance(error, commands.CommandNotFound):
            return

        # Handle specific errors
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`. Check usage with `!help`.")
        
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument provided. Please check your input.")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Command on cooldown. Try again in {error.retry_after:.1f}s.")
            
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have the required permissions to run this command.")

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions! Please check my role settings.")

        elif isinstance(error, commands.NotOwner):
            await ctx.send("🔒 This command is restricted to the bot owner.")
            
        else:
            # Unexpected Errors
            logger.error(f"Error in command {ctx.command}: {error}")
            traceback.print_exception(type(error), error, error.__traceback__)
            
            # Show Generic Error to User
            embed = discord.Embed(
                title="❌ Unexpected Error",
                description=f"An error occurred while executing `{ctx.command}`.\n```py\n{str(error)[:200]}```",
                color=discord.Color.red()
            )
            embed.set_footer(text="The error has been logged for review.")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
