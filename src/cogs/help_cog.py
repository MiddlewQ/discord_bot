import discord
from discord.ext import commands

from src.settings import logging
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
        embed = discord.Embed(
            title="📠 General Commands",
            description="Type `!<command>` to run any of the following commands.\nMore detailed help can be found by typing `!<command> help`.",
            color=discord.Color.blue()
        )
        # Print all commands
        for cmd in self.command_order:
            cmd = self.bot.get_command(cmd)
            embed.add_field(
                name=f"⚙️ {cmd.name}",
                value=cmd.help,
                inline=False
            )

        await ctx.send(embed=embed)
    
