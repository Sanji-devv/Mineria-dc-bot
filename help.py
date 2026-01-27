import discord
from discord.ext import commands

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Home", emoji="🏠", description="Return to main menu"),
            discord.SelectOption(label="Quick Commands", emoji="⚡", description="Quick actions: Roll, Loot, Wiki, Item"),
            discord.SelectOption(label="Registry & Tools", emoji="🛠️", description="Feat Check, Duplicate Check, Documents"),
            discord.SelectOption(label="Character Management", emoji="👤", description="Create and manage your characters"),
        ]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.from_rgb(46, 204, 113))
        
        if self.values[0] == "Home":
            embed.title = "📜 Mineria Bot - All Commands"
            embed.description = (
                "**⚡ Quick Commands**\n"
                "`!roll`, `!loot`, `!item`, `!wiki`, `!help`\n\n"
                "**🛠️ Registry & Tools**\n"
                "`!feat check`, `!d` (Duplicate Check), `!doc`\n\n"
                "**👤 Character Management**\n"
                "`!char create`, `!char dr`, `!char add/remove`, `!char save`\n"
                "`!char info`, `!char list`, `!char edit`, `!char rename`, `!char delete`"
            )
            
        elif self.values[0] == "Quick Commands":
            embed.title = "⚡ Quick Commands"
            embed.description = (
                "`!roll <expr>` - Roll dice (e.g., `!roll 2d20+5`).\n"
                "`!wiki` - Show official Wiki links.\n"
                "`!loot generate <CR> [count]` - Generate random loot.\n"
                "`!item listdown <gold>` - Find affordable items.\n"
                "`!help` - Shows this manual."
            )

        elif self.values[0] == "Registry & Tools":
            embed.title = "🛠️ Registry & Tools"
            embed.description = (
                "**Registry Checks** (Google Sheet Integration)\n"
                "`!feat check <name>` - Check if a feat/trait is available globally.\n"
                "`!d` (or `!dup`) - Check for illegal player duplicates (1 Ranked + 1 Clerk rule).\n\n"
                "**Documents**\n"
                "`!doc [name]` - List or download available files."
            )

        elif self.values[0] == "Character Management":
            embed.title = "👤 Character Management"
            embed.description = (
                "**Creation & Stats**\n"
                "`!char create <race>` - Start creating a character.\n"
                "`!char dr <stats>` - Distribute points & roll stats.\n"
                "`!char add <stat> <val>` - Add bonus to stat.\n"
                "`!char remove <stat> <val>` - Remove bonus from stat.\n"
                "`!rec [open|close]` - Toggle class recommendations.\n"
                "`!char save <name>` - Save created character.\n\n"
                "**Profile Management**\n"
                "`!char info [name]` - View character sheet.\n"
                "`!char list` - List all your characters.\n"
                "`!char edit <class|stat>` - Modify character details.\n"
                "`!char rename <old> <new>` - Rename a character.\n"
                "`!char delete <name>` - Delete a character."
            )

        embed.set_footer(text="Prefixes: !mineria or !m | Built for Pathfinder 1e")
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["m", "mineria", "h"])
    async def help_command(self, ctx: commands.Context):
        """Displays all available commands."""
        embed = discord.Embed(
            title="📜 Mineria Bot - All Commands",
            description=(
                "**⚡ Quick Commands**\n"
                "`!roll`, `!loot`, `!item`, `!wiki`, `!help`\n\n"
                "**🛠️ Registry & Tools**\n"
                "`!feat check`, `!d` (Duplicate Check), `!doc`\n\n"
                "**👤 Character Management**\n"
                "`!char create`, `!char dr`, `!char add/remove`, `!char save`\n"
                "`!char info`, `!char list`, `!char edit`, `!char rename`, `!char delete`"
            ),
            color=discord.Color.from_rgb(46, 204, 113)
        )
        embed.set_footer(text="Use the dropdown menu below to navigate.")
        
        view = HelpView()
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))