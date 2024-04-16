import discord
from discord.ext import commands
import os, asyncio
import logging

#import all of the cogs
from src.cogs.help_cog import help_cog
from src.cogs.music_cog import music_cog


# Loading token from .env file
from dotenv import load_dotenv
from typing import Final

# Logging
from src.utils.logging_config import *
from src.utils.partionation import PaginationView

logger = logging.getLogger("bot")

# Constants
load_dotenv()
TOKEN  = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('COMMAND_PREFIX')

intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Replace default help command with our own
bot.remove_command("help")



# Used to ignore music commands in DMs
def in_guild(ctx):
    if ctx.guild is None:
        return False
    return True


# Main Entry Point
async def main():
    async with bot:
        h_cog = help_cog(bot)
        m_cog = music_cog(bot)
        m_cog.cog_check(in_guild)

        await bot.add_cog(h_cog)
        logger.info("Help cog initialized and added to the bot.")

        await bot.add_cog(m_cog)
        logger.info("Music cog has been initialized and added to the bot.")
        
        await bot.start(TOKEN)
    
if __name__ == "__main__":
    asyncio.run(main())
