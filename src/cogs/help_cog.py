import discord
from discord.ext import commands
from src.utils.partionation import PaginationView
from src.utils.logging_config import logging
logger = logging.getLogger("bot")

class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.text_channel_list = []
        self.command_order = ['join', 'play', 'playing', 'multiplay', 'queue', 'pause', 'resume', 'skip', 'help', 'remove', 'clear', 'stop'] # used for ordering the help command


    def set_message(self):
        help_message = """
"""
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f'User {self.bot.user} (ID: {self.bot.user.id})')
        
        
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


    @commands.command(name="paginate")
    async def paginate(self, ctx):
        data = [

        ]

        for i in range(1,33):
            data.append({
                "label": "User Event",
                "item": f"User {i} has been added"
            })
        print(data)
        pagination_view = PaginationView(timeout=None)
        pagination_view.data = data
        await pagination_view.send(ctx, )

    @commands.command(name="ping")
    async def test_response_to_bot(self, ctx):
        await ctx.send("pong")

    
    @commands.command(name="help", aliases=["h"], help="Displays help message for all commands or a specific command.", extras="!help, !help <command>")
    async def help(self, ctx, *, command:str = None):
        if command:
            # Detailed help for single command
            await self.show_command_help(ctx, command)
            return
        
        # General Help Header
        # embed = discord.Embed(
        title="📠 General Commands"
        description="Type `!<command>` to run any of the following commands.\nMore detailed help can be found by typing `!<command> help`."
        # Print all commands
        data = {'fields': []}
        pagination_view = PaginationView()
        pagination_view.data = data
        pagination_view.title = title
        pagination_view.description = description
        for command in self.command_order:
            cmd = self.bot.get_command(command)
            data['fields'].append({
                'label': cmd.name,
                'item': cmd.help,
            })
        logger.debug("Fields: ", data['fields'])
        await pagination_view.send(ctx, )
    
