import discord
from discord.ext import commands
import os, asyncio
import logging

#import all of the cogs
from help_cog import help_cog
from music_cog import music_cog

# Loading token from .env file
from dotenv import load_dotenv
from typing import Final

# Handling for logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    handlers=[
                        logging.FileHandler("discord.log", encoding='utf-8', mode='w'),
                        logging.StreamHandler()  # This adds logging to the console as well
                    ])
# Constants
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
PREFIX: Final[str] = os.getenv('COMMAND_PREFIX')

intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Replace default help command with our own
bot.remove_command("help")


# Handling Bot Startup!
@bot.event
async def on_ready() -> None:
    print(f'{bot.user} has connected to Discord!')
    



# Main Entry Point
async def main():
    async with bot:
        await bot.add_cog(help_cog(bot))
        await bot.add_cog(music_cog(bot))
        await bot.start(TOKEN)
    
if __name__ == "__main__":
    asyncio.run(main())
