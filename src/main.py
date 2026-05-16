import discord
from discord.ext import commands
import os, sys
import asyncio
import logging

#import all of the cogs
from src.cogs.help_cog import help_cog
from src.cogs.music_cog import music_cog


# Loading token from .env file
from dotenv import load_dotenv

# Logging
from src.utils.logging_config import *


async def run_bot(prefix, token, logger):
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=prefix, intents=intents)
    bot.remove_command("help")
    
    async with bot:

        await bot.add_cog(help_cog(bot))
        logger.info("Help cog initialized and added to the bot.")

        await bot.add_cog(music_cog(bot))
        logger.info("Music cog has been initialized and added to the bot.")
        
        await bot.start(token)

async def main():
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    prefix = os.getenv("COMMAND_PREFIX")
    
    if prefix is None:
        print("No prefix found in environment file.", file=sys.stderr)
        sys.exit(1)
        
    if token is None:
        print("No discord bot token provided.", file=sys.stderr)
        sys.exit(1)

    logger = logging.getLogger("bot")

    await run_bot(prefix, token, logger) 
    
if __name__ == "__main__":
    asyncio.run(main())
