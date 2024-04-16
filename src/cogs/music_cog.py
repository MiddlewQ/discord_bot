import discord
import functools
import asyncio
from discord.ext import commands
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL

# from src.utils import *
from src.utils.logging_config import *
from src.utils.message import MessageStore as msg
from src.utils.time_convertion import *
from src.utils.partionation import PaginationView
from src.util import *

logger = logging.getLogger("music")

class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.is_playing = False
        self.is_paused = False
        self.current_song = None
        self.music_queue = []
        self.queue_duration = 0
        self.logger = logger
        
        self.YDL_OPTIONS = {'format': 'bestaudio/best'}
        self.FFMPEG_OPTIONS = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}

        self.vc = None
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)
        self.logger.info("Music cog initialized successfully.")


    def add_song_info(self, song, requester):
        embed = discord.Embed(
            title="",
            color=discord.Color.blue(),
            type='rich'
        )
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
        

    def search_yt(self, item):
        if item.startswith("https://"):
            search = self.ytdl.extract_info(item, download=False)
            if not search:
                return None
            video_info = {
                'source': item,
                'title': search['title'],
                'thumbnail': search['thumbnail'],
                'duration': search['duration']
            }
            return video_info
        # if item contains 'sabaton' lower- or upper-case have a 30 percent of playing metal machine

        
        search = VideosSearch(item, limit=1)
        if not search.result()['result']:
            return None
        result = search.result()['result'][0]

        
        video_info = {
            'source': result['link'],
            'title': result['title'],
            'thumbnail': result['thumbnails'][0]['url'],
            'duration': time_to_seconds_format(result['duration'])
        }
        return video_info

    @log_activity()
    async def play_next(self):
        if len(self.music_queue) == 0:
            self.is_playing = False
            self.is_paused = False
            self.queue_duration = 0
            self.current_song = None
            return
        self.is_playing = True

        #get the first url
        m_url = self.music_queue[0][0]['source']
        #remove the first element as you are currently playing it

        self.queue_duration -= self.current_song[0]['duration']
        self.current_song = self.music_queue.pop(0)
        
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
        data['url']

        self.vc.play(discord.FFmpegPCMAudio(
                data['url'], executable= "ffmpeg", **self.FFMPEG_OPTIONS), 
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
        logger.info(msg.LOG_PLAY_NEXT_REQUEST_EXECUTED.format(title=data['title']))
    
    # infinite loop checking 
    async def play_music(self, ctx):
        
        if len(self.music_queue) == 0:
            self.is_playing = False   
            return
        
        self.is_playing = True
        self.is_paused = False

        m_url = self.music_queue[0][0]['source']
        
        # Try to connect to voice channel if you are not already connected
        if self.vc == None or not self.vc.is_connected():
            self.vc = await self.music_queue[0][1].connect()

            #in case we fail to connect
            if self.vc == None:
                await ctx.send(embed=create_embed(msg.FAIL_CONNECT_TO_VOICE_CHANNEL))
                return
        else:
            await self.vc.move_to(self.music_queue[0][1])

        #remove the first element as you are currently playing it
        if self.current_song:
            self.queue_duration -= self.current_song[0]['duration']
        self.current_song = self.music_queue.pop(0)

        # Sonic Logic Magic - cool n' stuff
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
            self.vc.play(discord.FFmpegPCMAudio(data['url'], executable= "ffmpeg", **self.FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
            logger.info(msg.LOG_PLAY_MUSIC_EXECUTED.format(title=data['title']))
        except Exception as e:
            logger.error(e)
            await ctx.send(embed=create_embed(msg.FAIL_PLAYING_SONG))


    @commands.command(name="join", alias=['connect'], help=msg.HELP_MESSAGES['join'], extras=msg.HELP_USAGES['join'])
    @log_activity()
    async def join(self, ctx, *args):
        if not ctx.author.voice:    # Check if author is connected to a channel
            await ctx.send(embed=create_embed(msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            logger.warning(msg.LOG_SKIP_FAILED_USER_ABSENT)
            return

        if ctx.author.voice.channel == self.vc:
            await ctx.send(embed=create_embed(msg.FAIL_))
            logger.warning(msg.LOG_FAILED_PLAYING_SAME_CHANNEL)
            return
        
        channel = ctx.author.voice.channel      
        # If the bot is already playing music 
        if self.is_playing:
            if self.vc and self.vc.channel == channel:
                await ctx.send(embed=create_embed(msg.FAIL_PLAYING_SAME_CHANNEL))
                logger.warning(msg.LOG_FAILED_PLAYING_SAME_CHANNEL)
            else:
                await ctx.send(embed=create_embed(msg.FAIL_PLAYING_OTHER_CHANNEL))        
                logger.warning(msg.LOG_FAILED_PLAYING_SAME_CHANNEL)
            return
        
        if not self.vc or not self.vc.is_connected():     # if self.vc is None
            self.vc = await channel.connect()
            await ctx.send(embed=create_embed(f'Connected to {channel.name}'))
        elif self.vc.channel != channel:                  # Switch to the new server  
            self.vc = await self.vc.move_to(channel)
            await ctx.send(embed=create_embed(f":gear: Moved to {channel.name}"))
        else:
            await ctx.send(embed=create_embed(f":gear: I'm already in this channel."))


    @commands.command(name="play", aliases=["p", "pl"], help=msg.HELP_MESSAGES['play'], extras=msg.HELP_USAGES['play'])
    @log_activity()
    async def play(self, ctx, *args):
        if len(args) == 0:
            logger.warning(msg.LOG_PLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=create_embed(msg.FAIL_NO_ARGS))
            return
        if not ctx.author.voice or not ctx.author.voice.channel:
            logger.warning(msg.LOG_PLAY_FAILED_USER_NOT_IN_VOICE_CHANNEL.format(user=ctx.author.name))
            await ctx.send(embed=create_embed(msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            return
        
        query = " ".join(args)
        song = self.search_yt(query)
        if not song:
            logger.warning(msg.LOG_PLAY_FAILED_NOT_FOUND.format(query=query, user=ctx.author.name))
            await ctx.send(embed=create_embed(msg.FAIL_VIDEO_NOT_FOUND))
            return

        if self.is_playing:
            await ctx.send(embed=self.add_song_info(song, ctx.author))
        else:
            await ctx.send(embed=create_embed(msg.NOW_PLAYING.format(title=song['title'], source=song['source'])))  
        
        logger.info(msg.LOG_PLAY_ADD_TO_QUEUE_EXECUTED.format(title=song['title'], source=song['source']))
        self.music_queue.append([song, ctx.author.voice.channel])
        self.queue_duration += song['duration']

        if self.is_playing == False:
            await self.play_music(ctx)


    @commands.command(name="multiplay", aliases=["mp", "mplay", "mb"], help=msg.HELP_MESSAGES['multiplay'], extras=msg.HELP_USAGES['multiplay'])
    @log_activity()
    async def multiplay(self, ctx, *args):
        query = " ".join(args)
        if len(args) == 0:
            logger.warning(msg.LOG_MULTIPLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=create_embed(msg.FAIL_NO_ARGS))
            return 
        
        searches = [search.strip() for search in query.split('|')]
        number_of_songs = min(20, len(searches))
        for i in range(number_of_songs):
            search = searches[i]
            await self.play(ctx, *search.split())
        logger.info(msg.LOG_MULTIPLAY_EXECUTED.format(number_of_songs=number_of_songs))

    @commands.command(name="pause", help="Pauses the current song being played.", extras="!pause")
    @log_activity()
    async def pause(self, ctx, *args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            await ctx.send(embed=create_embed(":gear: Paused."))
            self.vc.pause()
        else:
            self.resume(ctx, *args)


    @commands.command(name = "resume", aliases=["r"], help=msg.HELP_MESSAGES['resume'], extras=msg.HELP_USAGES['resume'])
    @log_activity()
    async def resume(self, ctx, *args):
        user = ctx.author.name, 
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            logger.info(msg.LOG_RESUME_EXECUTED.format(user=user))
        logger.warning(msg.LOG_RESUME_FAILED_NOT_PAUSED.format(user=user))

    @commands.command(name="skip", aliases=["s"], help=msg.HELP_MESSAGES['skip'], extras=msg.HELP_USAGES['skip'])
    @log_activity()
    async def skip(self, ctx):
        user = ctx.author.name
        channel = ctx.author.voice.channel if ctx.author.voice and ctx.author.voice.channel else 'unknown'

        if not ctx.author.voice or not ctx.author.voice.channel:
            logger.warning(msg.LOG_JOIN_FAILED_USER_NOT_IN_VOICE_CHANNEL.format(user=user, channel=channel))            
            await ctx.send(embed=create_embed(msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            return
        if not self.vc or not self.vc.is_connected():
            logger.warning(msg.LOG_SKIP_FAILED_BOT_ABSENT.format(user=user, channel=channel))
            await ctx.send(embed=create_embed(msg.FAIL_BOT_NOT_IN_VOICE_CHANNEL))
            return
        if not self.current_song and not self.music_queue:
            logger.warning(msg.LOG_SKIP_FAILED_NO_MUSIC.format(user=user, channel=channel))
            await ctx.send(embed=create_embed(msg.FAIL_NO_MUSIC_PLAYING))
            return
        
        title = self.current_song[0]['title']
        source = self.current_song[0]['source']
        try:
            self.vc.stop()
            await ctx.send(embed=create_embed(msg.SONG_SKIPPED.format(title=title, source=source)))
            logger.info(msg.LOG_SONG_SKIPPED.format(title=title, user=user, guild=ctx.guild.name))
            await self.play_music(ctx)
        except Exception as e:
            logger.error(e)

    @commands.command(name="queue", aliases=["q"], help=msg.HELP_MESSAGES['queue'], extras=msg.HELP_USAGES['queue'])
    @log_activity()
    async def queue(self, ctx):
        user=ctx.author.name
        # Handle case no music in queue:
        if not self.current_song and not self.music_queue:
            await ctx.send(embed=create_embed(msg.QUEUE_EMPTY))
            logger.info(msg.LOG_QUEUE_EMPTY.format(channel=ctx.channel.name))
            return
        
        try:
            # Less than 10 songs
            song = self.current_song[0]
                # For more than 10 songs, create a scrollable list view 5 items at a time
            data = {
                'time_label': "Estimated Total Playtime",
                'time': f"{seconds_to_time_format(self.queue_duration)}",
                'thumbnail': f"{ctx.guild.icon.url}",
                'fields': [],
            }
            pagination_view = PaginationView()
            pagination_view.title =  msg.MUSIC_QUEUE_STATUS.format(channel_name=ctx.guild.voice_client.channel.name) 
            pagination_view.description = msg.NOW_PLAYING.format(title=song['title'], source=song['source'])
            pagination_view.data = data

            # pagination_view.set_thumbnail(url=self.bot.user.avatar.url)
            for queue_nbr, song_info in enumerate(self.music_queue, start=1):
                data['fields'].append({
                    'label': "",
                    'item': f"**{queue_nbr}.** {song_info[0]['title']}",
                })
            await pagination_view.send(ctx)
            number_of_songs = len(self.music_queue) + 1 if self.current_song else len(self.music_queue)
            logger.info(msg.LOG_QUEUE_DISPLAYED.format(channel=ctx.channel.name, number_of_songs=number_of_songs))
        except Exception as e:
            logger.error(e)


    @commands.command(name="playing", aliases=["np"], help=msg.HELP_MESSAGES['playing'], extras=msg.HELP_USAGES['playing'])
    @log_activity()
    async def playing(self, ctx):
        if self.is_playing:
            playing_msg = msg.PLAYING.format(title=self.current_song[0]['title'], source=self.current_song[0]['title'])
            await ctx.send(embed=create_embed(playing_msg))
            return
        
        title = self.current_song[0]['title']
        source = self.current_song[0]['source']
        await ctx.send(embed=create_embed(msg.PLAYING.format(title=title, source=source)))


    @commands.command(name="remove", aliases=["rm"], help=msg.HELP_MESSAGES['remove'], extras=msg.HELP_USAGES['remove'])
    @log_activity()
    async def remove(self, ctx, *args):
        if not self.music_queue:
            logger.warning(msg.LOG_REMOVE_FAILED_NO_QUEUE.format(user=ctx.author.name))
            await ctx.send(embed=create_embed(msg.FAIL_NO_MUSIC_IN_QUEUE))
            return
        
        # Removes last if no arg given
        if len(args) == 0:
            self.music_queue.pop()
            logger.info(msg.LOG_REMOVE_LAST_EXECUTED.format(index=len(self.music_queue, user={ctx.author.name})))
            await ctx.send(embed=create_embed(msg.REMOVED_LAST))
            return
        
        # Try to remove at the input index (queue starts at 1 for user)
        try:
            index = int(args[0]) - 1
            song = self.music_queue[index][0]
            self.queue_duration -= self.music_queue[index][0]['duration']
            self.music_queue.pop(index)
            logger.info(msg.REMOVED_QUEUE_INDEX.format(index=index))
            await ctx.send(embed=create_embed(msg.SONG_REMOVED.format(title=song['title'])))
        except Exception as e:
            logger.error(e)
            await ctx.send(embed=create_embed(msg.FAIL_INVALID_INDEX))
        

    @commands.command(name="clear", aliases=["c", "bin"], help=msg.HELP_MESSAGES['clear'], extras=msg.HELP_USAGES['clear'])
    @log_activity()
    async def clear(self, ctx):
        if self.vc != None and self.is_playing:
            self.vc.stop()

        self.is_playing = False
        self.music_queue = []
        self.current_song = None
        self.queue_duration = 0
        logger.info(msg.LOG_CLEAR_EXECUTED.format(user=ctx.author.name))
        await ctx.send(embed=create_embed(msg.QUEUE_CLEARED))

    @commands.command(name="stop", aliases=["disconnect"], help=msg.HELP_MESSAGES['stop'], extras=msg.HELP_USAGES['stop'])
    @log_activity()
    async def stop(self, ctx):
        self.is_playing = False
        self.is_paused = False
    
        # Clear the current song and the music queue
        if self.current_song and self.music_queue:
            logger.info()
            self.current_song = None
            self.music_queue.clear() 
        
        self.queue_duration = 0 

        if self.vc:
            await self.vc.disconnect()
            self.vc = None
        logger.info(msg.LOG_STOP_EXECUTED.format(channel=ctx.author.voice.channel.name, user=ctx.author.name))


    @commands.command(name="status", aliases=["stat"], help=msg.HELP_MESSAGES['status'], extras=msg.HELP_USAGES['status'])
    @log_activity()
    async def status(self, ctx):
        songs = []
        for i in range(len(self.music_queue)):
            songs.append(self.music_queue[i][0]['title'])        
        
        status_description = (    
            f"Playing: {self.is_playing}\n"
            f"Paused: {self.is_paused}\n"
            # f"Current Song: {self.current_song[0]['title'] if self.current_song else 'None'}\n"           | Not used, do !queue instead
            # f"Queue: {', '.join(songs)}\n"  # Join the song URLs with a comma and a space
            f"Queue Duration: {self.queue_duration}\n"
            f"Voice Channel: {self.vc.channel.name if self.vc and self.vc.is_connected() else 'Not connected'}"
        )
        
        embed = discord.Embed(
            title=":gear: Bot Status :gear:",
            description=status_description,
            color=discord.Color.blue()
        )
        # logger.info(msg.LOG_STATUS)
        await ctx.send(embed=embed)

