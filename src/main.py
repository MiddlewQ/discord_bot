import discord
from discord.ext import commands
import os, sys
import asyncio
import logging
import signal

#import all of the cogs
from src.cogs.help_cog import HelpCog
from src.cogs.audio_cog import AudioCog


# Loading token from .env file
from dotenv import load_dotenv

# Logging
from src.utils.logging_config import *


async def run_bot(prefix, token, logger):
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=prefix, intents=intents)
    bot.remove_command("help")

    # Ctrl+C and Docker's stop signal both close the bot cleanly: leave voice, then disconnect
    loop = asyncio.get_running_loop()
    shutdown_tasks: set[asyncio.Task] = set()  # asyncio only keeps weak references to tasks

    def on_signal(sig: signal.Signals) -> None:
        task = asyncio.create_task(shutdown(bot, sig, logger))
        shutdown_tasks.add(task)
        task.add_done_callback(shutdown_tasks.discard)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, on_signal, sig)

    async with bot:

        await bot.add_cog(HelpCog(bot))
        logger.info("HelpCog initialized and added to the bot.")

        await bot.add_cog(AudioCog(bot))
        logger.info("AudioCog has been initialized and added to the bot.")
        
        await bot.start(token)

async def shutdown(bot: commands.Bot, sig: signal.Signals, logger: logging.Logger) -> None:
    if bot.is_closed():
        return

    logger.info(f"Received {sig.name}, shutting down.")
    await bot.close()


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
    logger.info("Bot shut down.")

if __name__ == "__main__":
    asyncio.run(main())
