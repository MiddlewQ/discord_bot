import logging
import discord
from discord.ext import commands
import functools

logger = logging.getLogger("music")
                      
# Decorator for activity logging
def log_activity():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = args[1] if len(args) > 1 and isinstance(args[1], commands.Context) else None
            if ctx:
                user = ctx.author.name
                channel = ctx.author.voice.channel if ctx.author.voice and ctx.author.voice.channel else 'unknown'
                log_message = f"Activity '{func.__name__}' requested by '{user}' in channel '{channel}'."
            else:
                log_message = f"Activity '{func.__name__}' executed without context."
            logger.info(log_message)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# General embed creation utility
def create_embed(description=None, title=None, url=None, color=0x3498db):
    embed = discord.Embed(description=description, title=title, url=url, color=color)
    return embed

