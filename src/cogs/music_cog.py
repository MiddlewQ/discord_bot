import discord
# import functools
import asyncio
from discord.ext import commands
from yt_dlp import YoutubeDL

# from src.utils import *
from src.utils.logging_config import *
from src.utils.message import MessageStore as msg
from src.utils.time_convertion import *
from src.utils.partionation import PaginationView

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
        
        self.YDL_OPTIONS = {'format': 'bestaudio[ext=m4a]/bestaudio/best', "noplaylist": True}
        self.FFMPEG_OPTIONS = {'options':        '-vn', 
                               'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -http_persistent 0' }

        self.text_channel = None
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
        

    def search_yt(self, query):
        if not query.startswith("http"):     
            query = f"ytsearch:{query}"

        info = self.ytdl.extract_info(query, download=False)

        if not info:
            return None

        entry = info.get("entries")[0]
        if not entry:
            return None

        thumb = entry.get("thumbnail")
        if not thumb:
            thumbs = entry.get("thumbnails") or []
            if thumbs:
                last_url = thumbs[-1].get("url")
                first_url = thumbs[0].get("url")
                thumb = last_url if last_url else first_url

        return {
            'source': entry.get('webpage_url') or entry.get("original_url"),
            'title': entry.get('title'),
            'thumbnail': thumb,
            'duration': entry.get('duration') or 0,
        }

    @commands.Cog.listener()
    async def on_command(self, ctx):
        logger.info(f"{ctx.command.name.capitalize()} command requested: User {ctx.author.name} in {ctx.channel.name}")

    async def play_next(self):

        if len(self.music_queue) == 0:
            self.is_playing = False
            self.is_paused = False
            self.queue_duration = 0
            self.current_song = None
            return
        
        self.is_playing = True
        
        next_item = self.music_queue.pop(0)
        next_song = next_item[0]
        self.current = next_item
        #remove the first element as you are currently playing it

        self.queue_duration -= max(0, self.queue_duration - (next_song.get('duration') or 0))
        self.current_song = self.music_queue.pop(0)

        query = next_song['source']

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(query, download=False))

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
                await ctx.send(embed=discord.Embed(description=msg.FAIL_CONNECT_TO_VOICE_CHANNEL))
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
            song = data['url']
            self.vc.play(discord.FFmpegPCMAudio(song, executable= "ffmpeg", **self.FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
            
            logger.info(msg.LOG_PLAY_MUSIC_EXECUTED.format(title=data['title']))
        except Exception as e:
            logger.error(e)
            await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYING_SONG))


    @commands.command(name="join", aliases=['connect'], help=msg.HELP_MESSAGES['join'], extras=msg.HELP_USAGES['join'])
    async def join(self, ctx, *args):
        if not ctx.author.voice:    # Check if author is connected to a channel
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            logger.warning(msg.LOG_SKIP_FAILED_USER_ABSENT)
            return
        
        channel: discord.VoiceChannel = ctx.author.voice.channel      

        # If the bot is already playing music 
        if self.is_playing:
            if self.vc and self.vc.channel == channel:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYING_SAME_CHANNEL))
                logger.warning(msg.LOG_PLAY_FAILED_USER_CHANNEL_SAME.format(user=ctx.author.name))
            else:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYING_OTHER_CHANNEL))        
                logger.warning(msg.LOG_PLAY_FAILED_USER_CHANNEL_OTHER.format(user=ctx.author.name))
            return
        
        if not self.vc or not self.vc.is_connected():
            self.vc = await channel.connect()
            logger.info(msg.LOG_JOIN_CHANNEL_CONNECT.format(channel=self.vc.channel.name))
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_CONNECTED.format(channel=channel.name)))
        elif self.vc.channel != channel:
            old = self.vc.channel.name
            await self.vc.move_to(channel)
            logger.info(msg.LOG_JOIN_CHANNEL_MOVE.format(old=old, new=channel.name))
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_MOVED.format(channel=channel.name)))
        else:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_ALREADY_CONNECTED.format(channel=channel.name)))
            logger.warning(msg.LOG_PLAY_FAILED_USER_CHANNEL_SAME.format(user=ctx.author.name))
            

    @commands.command(name="play", aliases=["p", "pl"], help=msg.HELP_MESSAGES['play'], extras=msg.HELP_USAGES['play'])
    async def play(self, ctx, *args):
        if len(args) == 0:
            logger.warning(msg.LOG_PLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_NO_ARGS))
            return
        if not ctx.author.voice or not ctx.author.voice.channel:
            logger.warning(msg.LOG_PLAY_FAILED_USER_ABSENT.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            return
        
        query = " ".join(args)
        song = self.search_yt(query)

        if not song:
            logger.warning(msg.LOG_PLAY_FAILED_NOT_FOUND.format(query=query, user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_VIDEO_NOT_FOUND))
            return

        if song['duration'] > 1200:
            logger.warning(msg.LOG_PLAY_FAILED_TOO_LONG.format(query=query, user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_VIDEO_TOO_LONG))
            return

        if self.is_playing:
            await ctx.send(embed=self.add_song_info(song, ctx.author))
        else:
            await ctx.send(embed=discord.Embed(description=msg.NOW_PLAYING.format(title=song['title'], source=song['source'])))  
        
        logger.info(msg.LOG_PLAY_ADD_TO_QUEUE_EXECUTED.format(title=song['title'], source=song['source']))
        self.music_queue.append([song, ctx.author.voice.channel])
        self.queue_duration += song['duration'] 

        if self.is_playing == False:
            await self.play_music(ctx)


    @commands.command(name="multiplay", aliases=["mp", "mplay", "mb"], help=msg.HELP_MESSAGES['multiplay'], extras=msg.HELP_USAGES['multiplay'])
    async def multiplay(self, ctx, *args):
        query = " ".join(args)
        if len(args) == 0:
            logger.warning(msg.LOG_MULTIPLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_NO_ARGS))
            return 
        
        searches = [search.strip() for search in query.split('|')]
        number_of_songs = min(20, len(searches))
        for i in range(number_of_songs):
            search = searches[i]
            await self.play(ctx, *search.split())
        logger.info(msg.LOG_MULTIPLAY_EXECUTED.format(number_of_songs=number_of_songs))


    @commands.command(name="pause", help="Pauses the current song being played.", extras="!pause")
    async def pause(self, ctx, *args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            await ctx.send(embed=discord.Embed(description=":gear: Paused."))
            self.vc.pause()
        else:
            await self.resume(ctx, *args)


    @commands.command(name = "resume", aliases=["r"], help=msg.HELP_MESSAGES['resume'], extras=msg.HELP_USAGES['resume'])
    async def resume(self, ctx, *args):
        user = ctx.author.name 
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            logger.info(msg.LOG_RESUME_EXECUTED.format(user=user))
        else:
            logger.warning(msg.LOG_RESUME_FAILED_NOT_PAUSED.format(user=user))


    @commands.command(name="skip", aliases=["s"], help=msg.HELP_MESSAGES['skip'], extras=msg.HELP_USAGES['skip'])
    async def skip(self, ctx):
        user = ctx.author.name
        channel = ctx.author.voice.channel if ctx.author.voice and ctx.author.voice.channel else 'unknown'

        if not ctx.author.voice or not ctx.author.voice.channel:
            logger.warning(msg.LOG_JOIN_FAILED_USER_ABSENT.format(user=user, channel=channel))            
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            return
        
        if not self.vc or not self.vc.is_connected():
            logger.warning(msg.LOG_SKIP_FAILED_BOT_ABSENT.format(user=user, channel=channel))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_IN_VOICE_CHANNEL))
            return
        
        if not self.current_song and not self.music_queue:
            logger.warning(msg.LOG_SKIP_FAILED_NO_MUSIC.format(user=user, channel=channel))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_SKIP_SONG))
            return
        
        title = self.current_song[0]['title']
        source = self.current_song[0]['source']
        try:
            self.vc.stop()
            await ctx.send(embed=discord.Embed(description=msg.SKIP_SONG.format(title=title, source=source)))
            logger.info(msg.LOG_SONG_SKIPPED.format(title=title, user=user, guild=ctx.guild.name))
        except Exception as e:
            logger.error(e)

    @commands.command(name="queue", aliases=["q"], help=msg.HELP_MESSAGES['queue'], extras=msg.HELP_USAGES['queue'])
    async def queue(self, ctx):
        user=ctx.author.name
        # Handle case no music in queue:
        if not self.current_song and not self.music_queue:
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_EMPTY))
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
            pagination_view.title =  msg.QUEUE_STATUS.format(channel_name=ctx.guild.voice_client.channel.name) 
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
    async def playing(self, ctx):
        title = self.current_song[0]['title']
        source = self.current_song[0]['source']
        if self.is_playing:
            playing_msg = msg.PLAYING.format(title=title, source=source)
            await ctx.send(embed=discord.Embed(description=playing_msg))
            return
        
        await ctx.send(embed=discord.Embed(description=msg.PLAYING.format(title=title, source=source)))


    @commands.command(name="remove", aliases=["rm"], help=msg.HELP_MESSAGES['remove'], extras=msg.HELP_USAGES['remove'])
    async def remove(self, ctx, *args):
        if not self.music_queue:
            logger.warning(msg.LOG_REMOVE_FAILED_NO_QUEUE.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_QUEUE_EMPTY))
            return
        
        # Removes last if no arg given
        if len(args) == 0:
            song = self.music_queue.pop()[0]
            self.queue_duration -= song['duration']
            
            logger.info(msg.LOG_REMOVE_LAST_EXECUTED.format(index=len(self.music_queue), user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.REMOVED_QUEUE_LAST))
            return
        
        # Try to remove at the input index (queue starts at 1 for user)
        try:
            index = int(args[0]) - 1
            song = self.music_queue[index][0]
            self.queue_duration -= self.music_queue[index][0]['duration']
            self.music_queue.pop(index)
            logger.info(msg.REMOVED_QUEUE_INDEX.format(index=index))
            await ctx.send(embed=discord.Embed(description=msg.SONG_REMOVED.format(title=song['title'])))
        except Exception as e:
            logger.error(e)
            await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_INDEX))
        

    @commands.command(name="clear", aliases=["c", "bin"], help=msg.HELP_MESSAGES['clear'], extras=msg.HELP_USAGES['clear'])
    async def clear(self, ctx):
        if self.vc != None and self.is_playing:
            self.vc.stop()

        self.is_playing = False
        self.music_queue = []
        self.current_song = None
        self.queue_duration = 0
        user = ctx.author.name
        if user is None:
            user = "<Unknown>"
        logger.info(msg.LOG_CLEAR_EXECUTED.format(user=user))
        await ctx.send(embed=discord.Embed(description=msg.QUEUE_CLEARED))

    @commands.command(name="stop", aliases=["disconnect"], help=msg.HELP_MESSAGES['stop'], extras=msg.HELP_USAGES['stop'])
    async def stop(self, ctx):
        self.is_playing = False
        self.is_paused = False
    
        # Clear the current song and the music queue
        if self.current_song or self.music_queue:
            logger.info(msg.LOG_STOP_EXECUTED)
            self.current_song = None
            self.music_queue.clear()    
            self.queue_duration = 0     
        

        if self.vc:
            await self.vc.disconnect()
            self.vc = None
        logger.info(msg.LOG_STOP_EXECUTED.format(channel=ctx.author.voice.channel.name, user=ctx.author.name))


    @commands.command(name="status", aliases=["stat"], help=msg.HELP_MESSAGES['status'], extras=msg.HELP_USAGES['status'])
    async def status(self, ctx):
        songs = []
        for i in range(len(self.music_queue)):
            songs.append(self.music_queue[i][0]['title'])        
        
        status_description = (    
            f"Playing: {self.is_playing}\n"
            f"Paused: {self.is_paused}\n"
            f"Current Song: {self.current_song[0]['title'] if self.current_song else 'None'}\n"           # | Not used, do !queue instead
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

