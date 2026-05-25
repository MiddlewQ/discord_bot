import discord
from discord.ext import commands
from src.utils.partionation import PaginationView
from src.utils.logging_config import logging
logger = logging.getLogger("bot")

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.text_channel_list = []
        self.command_order = ['join', 'play', 'playing', 'multiplay', 'queue', 'pause', 'resume', 'skip', 'help', 'remove', 'clear', 'stop'] # used for ordering the help command

    @commands.Cog.listener()
    async def on_ready(self):
        bot_user = self.bot.user

        if bot_user is None:
            logger.warning("Bot is ready but self.bot.user is None.")
            return
                
        logger.info(f'User {self.bot.user} (ID: {bot_user.id})')
        
        
    async def show_command_help(self, ctx, command):
        cmd = self.bot.get_command(command)
        if cmd:
            embed = discord.Embed(
                title=f"⚙️ {cmd.name.capitalize()}",
                description=cmd.help,
                color=discord.Color.blue()
            )
            embed.add_field(name="Usage", value=cmd.extras, inline=True)
            embed.add_field(name="Shortcut", value=", ".join(cmd.aliases) if cmd.aliases else "", inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=discord.Embed(
                title="⚙️ Error", 
                description="Command not found.", 
                color=discord.Color.blue()
            ))

    @commands.command(name="ping")
    async def test_response_to_bot(self, ctx):
        await ctx.send("pong")

    
    @commands.command(name="help", aliases=["h"], help="Displays help message for all commands or a specific command.", usage="!help, !help <command>")
    async def help(self, ctx, *, command:str | None = None):
        data = {"fields": []}

        for command_name in self.command_order:
            cmd = self.bot.get_command(command_name)

            if cmd is None:
                continue

            data["fields"].append({
            "label": cmd.name,
            "item": cmd.help or "No help text available.",
            })

        pagination_view = PaginationView(
            data=data,
            title="📠 General Commands",
            description=(
                "Type `!<command>` to run any of the following commands.\n"
                "More detailed help can be found by typing `!help <command>`."
            ),
            timeout=None,
        )

        await pagination_view.send(ctx)