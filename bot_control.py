import discord
from discord.ext import commands, tasks

class BotControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.presence_task.start()

    def cog_unload(self):
        self.presence_task.cancel()

    @tasks.loop(minutes=5)
    async def presence_task(self):
        """
        Ensures the bot remains online and displays specific activity text.
        """
        await self.bot.wait_until_ready()
        try:
            # "Game" activity type shows as "Playing !m ve !roll"
            activity = discord.Game(name="!m ve !roll")
            await self.bot.change_presence(status=discord.Status.online, activity=activity)
        except Exception as e:
            print(f"Failed to update presence: {e}")

    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync_tree(self, ctx):
        """
        Syncs the slash command tree to Discord. 
        Useful if commands don't show up in the profile.
        """
        msg = await ctx.send("🔄 Syncing commands...")
        try:
            synced = await self.bot.tree.sync()
            await msg.edit(content=f"✅ Synced **{len(synced)}** commands globally.")
        except Exception as e:
            await msg.edit(content=f"❌ Sync failed: {e}")

async def setup(bot):
    await bot.add_cog(BotControl(bot))
