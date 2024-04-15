import logging
import discord
import functools
from functools import wraps

logger = logging.getLogger(__name__)

# Decorator

def log_activity():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = None
            # Assume the first argument is ctx if it's a command; adjust based on your usage
            if args and hasattr(args[0], 'author'):
                ctx = args[0]
            
            if ctx:
                user = ctx.author.name
                channel = ctx.author.voice.channel if ctx.author.voice and ctx.author.voice.channel else 'unknown'
                log_message = f"Activity {func.__name__} requested by {user} in channel {channel}."
            else:
                log_message = f"Activity {func.__name__} executed."
            
            logger.info(log_message)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def create_embed(description=None, title=None, url=None, color=0x3498db):
    embed = discord.Embed(description=description, url=url, color=color)
    if title:
        embed.title = title
    if url:
        embed.url = url
    return embed

def add_song_info(self, song, requester):
    embed = create_embed()
    embed.set_author(icon_url=self.bot.user.avatar.url, name="Added track")
    fields = [
        # Name, value, inline
        ("Track", f"[{song['title']}]({song['source']})", False),
        ("", "", False),
        ("Estimated time until played", f"{seconds_to_time_format(self.queue_duration)}", True),
        ("Track length", f"{seconds_to_time_format(song['duration'])}", True),
        ("", "", True),
        ("Position in upcoming", f"{len(self.music_queue) if len(self.music_queue) > 0 else 'Next'}", True),
        ("Position in queue", f"{len(self.music_queue)+1}", True),
        ("", "", True)
    ]
    for name, val, inline in fields:
        embed.add_field(name=name, value=val, inline=inline)   

    embed.set_thumbnail(url=song['thumbnail'])
    embed.set_footer(icon_url=requester.avatar.url, text=f"requested by {str(requester).capitalize()}") 
    return embed

def seconds_to_time_format(total_seconds):
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return (f"{hours:02}:{minutes:02}:{seconds:02}")
    else:
        return (f"{minutes:02}:{seconds:02}")


def time_to_seconds_format(duration: str):
    parts = duration.split(':')
    parts = [int(part) for part in parts]
    seconds = 0
    minutes = 0
    hours = 0
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        minutes, seconds = parts
    else:
        seconds = parts[0]
    return hours * 3600 + minutes * 60 + seconds
