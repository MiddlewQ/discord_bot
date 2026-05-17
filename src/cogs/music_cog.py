import discord
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
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        self.current_song = None
        self.music_queue = []
        self.queue_duration = 0
        self.logger = logger
        
        self.YDL_OPTIONS = {'format': 'bestaudio[ext=m4a]/bestaudio/best', 
                            'noplaylist': True}
        self.FFMPEG_OPTIONS = {'options':        '-vn', 
                               'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5' }

        self.session_text_channel: discord.abc.Messageable | None = None
        self.vc = None
        self.ytdl = YoutubeDL(self.YDL_OPTIONS) # type: ignore
        self.logger.info("Music cog initialized successfully.")

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    # State helpers
    def get_vc(self) -> discord.VoiceClient | None:
        if self.vc is not None and self.vc.is_connected():
            return self.vc
        return None

    def set_session_text_channel_once(self, ctx):
        if self.session_text_channel is None:
            self.session_text_channel = ctx.channel


    # Embed / yt-dlp helders

    def add_song_info(self, song, requester):
        embed = discord.Embed(
            title="",
            color=discord.Color.blue(),
            type='rich'
        )
        bot_user = self.bot.user
        icon_url = bot_user.display_avatar.url if bot_user is not None else None
        embed.set_author(icon_url=icon_url, name="Added track")
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
        

    async def search_yt(self, query):
        loop = asyncio.get_running_loop()

        search_query = query if query.startswith("http") else f"ytsearch1:{query}"

        info = await loop.run_in_executor(
            None,
            lambda: self.ytdl.extract_info(search_query, download=False)
        )

        if not isinstance(info, dict):
            return None

        entries = info.get("entries")

        if isinstance(entries, list) and entries:
            maybe_entry = entries[0]
        else:
            maybe_entry = info if info.get("webpage_url") or info.get("url") else None

        if not isinstance(maybe_entry, dict):
            return None
        entry = maybe_entry 

        thumb = entry.get("thumbnail")
        if not thumb:
            thumbs = entry.get("thumbnails") or []
            if isinstance(thumbs, list) and thumbs:
                first = thumbs[0]
                last = thumbs[-1]

                first_url = thumbs[0].get("url") if isinstance(first, dict) else None
                last_url = first.get("url") if isinstance(last, dict) else None

                thumb = first_url or last_url

        return {
            'source': entry.get('webpage_url') or entry.get("original_url"),
            'title': entry.get('title'),
            'thumbnail': thumb,
            'duration': entry.get('duration') or 0,
        }

    # 4. Core playback internals
    async def play_music(self, ctx):
        if not self.music_queue:
            self.current_song = None
            return
        
        queue_item = self.music_queue[0]
        song_info = queue_item[0]
        channel = queue_item[1]

        source = song_info.get("source")
        if not isinstance(source, str) or not source:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYING_SONG))

        vc = self.get_vc()
        # Try to connect to voice channel if you are not already connected
        if vc is None:
            vc = await channel.connect()
            self.vc = vc
        elif vc.channel != channel:
            await vc.move_to(channel)
        
        try:
            loop = asyncio.get_event_loop()

            data = await loop.run_in_executor(
                None, 
                lambda: self.ytdl.extract_info(source, download=False)
            )

            if not isinstance(data, dict):
                raise ValueError("yt-dlp returnd invalid data")
            
            stream_url = data.get("url") 
            title = data.get("title") or "Unknown title"

            if not isinstance(stream_url, str) or not stream_url:
                raise ValueError(f"No valid stream URL found for {title}")
            
            self.current_song = self.music_queue.pop(0)

            vc.play(
                discord.FFmpegPCMAudio(
                    stream_url, 
                    executable= "ffmpeg", 
                    options=self.FFMPEG_OPTIONS["options"],
                    before_options=self.FFMPEG_OPTIONS["before_options"]
                ), 
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)
            )            
            logger.info(msg.LOG_PLAY_MUSIC_EXECUTED.format(title=title))

        except Exception:
            logger.exception("Failed to play music.")
            await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYING_SONG))


    async def play_next(self):
        if len(self.music_queue) == 0:
            self.queue_duration = 0
            self.current_song = None
            return
        
        if self.vc is None:
            logger.warning("Tried to play next song, but voice client is None")
            return
        
        
        next_item = self.music_queue.pop(0)
        next_song = next_item[0]
        self.current_song = next_item
        

        self.queue_duration -= next_song.get("duration") or 0

        query = next_song['source']

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(query, download=False))

        if not isinstance(data, dict):
            logger.warning("yt-dlop return invalid data")
            await self.play_next()
            return
        url = data.get("url")
        if not isinstance(url, str):
            logger.warning("Could not get audio URL from yt-dlp result")
            await self.play_next()
            return
        
        title = data.get("title") or "Unknown title"

        self.vc.play(
            discord.FFmpegPCMAudio(
                url, 
                executable= "ffmpeg", 
                options=self.FFMPEG_OPTIONS["options"],
                before_options=self.FFMPEG_OPTIONS["before_options"]
            ), 
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_next(), 
                self.bot.loop
            )
        )
        logger.info(msg.LOG_PLAY_NEXT_REQUEST_EXECUTED.format(title=title))
    
    # 5. Idle / cleanup internals
    def start_idle_timer(self, seconds: int, reason: str):
        self.cancel_idle_timer()
        self.idle_task = self.bot.loop.create_task(
            self.idle_disconnect_after(seconds, reason)
        )

    def cancel_idle_timer(self):
        if self.idle_task is not None:
            self.idle_task.cancel()
            self.idle_task = None

    async def idle_disconnect_after(self, seconds: int, reason: str):
        try:
            await asyncio.sleep(seconds)

            await self.cleanup_voice(reason)
        except asyncio.CancelledError:
            pass

    async def cleanup_voice(self, reason):
        vc = self.get_vc()

        if vc is not None:
            await vc.disconnect()
        
        self.music_queue.clear()
        self.current_song = None
        self.queue_duration = 0
        self.vc = None

        logger.info(f"Disconnected from voice to due to inactivity: {reason}")

        if self.session_text_channel is not None:
            await self.session_text_channel.send(
                embed=discord.Embed(
                    description=f"Disconnected due to inactivity: {reason}"
                )
        )

    # 6. Listeners
    @commands.Cog.listener()
    async def on_command(self, ctx):
        logger.info(f"{ctx.command.name.capitalize()} command requested: User {ctx.author.name} in {ctx.channel.name}")


    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if self.bot.user is not None and member.id == self.bot.user.id:
            return

        vc = self.get_vc()
        if vc is None or vc.channel is None:
            return
        
        if before.channel != vc.channel and after.channel != vc.channel:
            return
        
        humans = [m for m in vc.channel.members if not m.bot]

        if len(humans) == 0:
            self.start_idle_timer(120, "") # Leave voice call after 2 min alone
        else:
            self.cancel_idle_timer()


    # 7. Commands
    @commands.command(name="join", aliases=['connect'], help=msg.HELP_MESSAGES['join'], usage=msg.HELP_USAGES['join'])
    async def join(self, ctx, *args):
        self.set_session_text_channel_once(ctx)

        voice = ctx.author.voice
        if voice is None or voice.channel is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            logger.warning(msg.LOG_SKIP_FAILED_USER_ABSENT)
            return
        
        channel = voice.channel
        vc = self.get_vc()

        if vc is None:
            self.vc = await channel.connect()
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_CONNECTED.format(channel=channel.name)))
            logger.info(msg.LOG_JOIN_CHANNEL_CONNECT)
            return

        if vc.channel == channel:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYING_SAME_CHANNEL))
            logger.warning(msg.LOG_PLAY_FAILED_USER_CHANNEL_SAME.format(user=ctx.author.name))
            return  

        if vc.is_playing() or vc.is_paused():
            await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYING_OTHER_CHANNEL))        
            logger.warning(msg.LOG_PLAY_FAILED_USER_CHANNEL_OTHER.format(user=ctx.author.name))
            return
        
        old_channel = vc.channel.name
        await vc.move_to(channel)
        
        await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_MOVED.format(channel=channel.name)))
        logger.info(msg.LOG_JOIN_CHANNEL_MOVE.format(old=old_channel, new=channel.name))


    @commands.command(name="play", aliases=["p", "pl"], help=msg.HELP_MESSAGES['play'], usage=msg.HELP_USAGES['play'])
    async def play(self, ctx, *args):
        self.cancel_idle_timer()
        self.set_session_text_channel_once(ctx)
        user = ctx.author.name
        
        if not args:
            logger.warning(msg.LOG_PLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_NO_ARGS))
            return
        
        voice = ctx.author.voice
        if voice is None or voice.channel is None:
            logger.warning(msg.LOG_PLAY_FAILED_USER_ABSENT.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            return
        
        channel = voice.channel
        query = " ".join(args)

        song = await self.search_yt(query)

        if song is None:
            logger.warning(msg.LOG_PLAY_FAILED_NOT_FOUND.format(query=query, user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_VIDEO_NOT_FOUND))
            return
        
        title = song.get("title") or "Unknown title"
        source = song.get("source")
        duration = song.get("duration") or 0

        if not isinstance(source, str) or not source:
            logger.warning(msg.LOG_PLAY_FAILED_NOT_FOUND.format(query=query, user=user))

        if duration > 1200:
            logger.warning(msg.LOG_PLAY_FAILED_TOO_LONG.format(query=query, user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_VIDEO_TOO_LONG))
            return

        vc = self.get_vc()

        already_active = vc is not None and (vc.is_playing() or vc.is_paused())

        if already_active:
            await ctx.send(embed=self.add_song_info(song, ctx.author))
        else:
            await ctx.send(embed=discord.Embed(description=msg.NOW_PLAYING.format(title=title, source=source)))  
        
        self.music_queue.append([song, channel])
        self.queue_duration += duration

        logger.info(msg.LOG_PLAY_ADD_TO_QUEUE_EXECUTED.format(title=title, source=source))

        if not already_active:
            await self.play_music(ctx)


    @commands.command(name="multiplay", aliases=["mp", "mplay", "mb"], help=msg.HELP_MESSAGES['multiplay'], usage=msg.HELP_USAGES['multiplay'])
    async def multiplay(self, ctx, *args):
        if not args:
            logger.warning
            logger.warning(msg.LOG_MULTIPLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_NO_ARGS))
            return 
        
        query = " ".join(args)
        
        searches = [
            search.strip() 
            for search in query.split('|')
            if search.strip()
        ]
        
        if not searches:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_NO_ARGS))

        if len(searches) > 20:
            await ctx.send(embed=discord.Embed(description=":gear: Maximum 20 searches allowed for single message."))
            searches = searches[:20]

        for search in searches:
            await self.play(ctx, *search.split())

        logger.info(msg.LOG_MULTIPLAY_EXECUTED.format(number_of_songs=len(searches)))


    @commands.command(name="pause", help="Pauses the current song being played.", usage="!pause")
    async def pause(self, ctx, *args):
        vc = self.get_vc()

        if vc is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
            return 

        if vc.is_playing():
            vc.pause()
            await ctx.send(embed=discord.Embed(description=msg.PAUSED))
            return
        
        if vc.is_paused():
            await self.resume(ctx, *args)
            return 

        await ctx.send(embed=discord.Embed(description=msg.FAIL_SKIP_SONG))
        

    @commands.command(name = "resume", aliases=["r"], help=msg.HELP_MESSAGES['resume'], usage=msg.HELP_USAGES['resume'])
    async def resume(self, ctx, *args):
        user = ctx.author.name 
        vc = self.get_vc()

        if vc is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
            return            

        if vc.is_playing():
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_ALREADY_PLAYING))
            return

        if vc.is_paused():
            vc.resume()
            await ctx.send(embed=discord.Embed(description=msg.RESUME))
            logger.info(msg.LOG_RESUME_EXECUTED.format(user=user))
            return

        await ctx.send(embed=discord.Embed(description=msg.LOG_RESUME_FAILED_NOT_PAUSED))
        logger.warning(msg.LOG_RESUME_FAILED_NOT_PAUSED.format(user=user))


    @commands.command(name="skip", aliases=["s"], help=msg.HELP_MESSAGES['skip'], usage=msg.HELP_USAGES['skip'])
    async def skip(self, ctx):
        user = ctx.author.name


        voice = ctx.author.voice
        if not voice or not voice.channel:
            logger.warning(msg.LOG_JOIN_FAILED_USER_ABSENT.format(user=user, channel="unknown"))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_IN_VOICE_CHANNEL))
            return
        
        channel = voice.channel.name

        vc = self.get_vc()
        if vc is None:
            logger.warning(msg.LOG_SKIP_FAILED_BOT_ABSENT.format(user=user, channel=channel))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_IN_VOICE_CHANNEL))
            return
        
        if self.current_song is None:
            logger.warning(msg.LOG_SKIP_FAILED_NO_MUSIC.format(user=user, channel=channel))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_SKIP_SONG))
            return
        
        if not vc.is_playing() and not vc.is_paused():
            logger.warning(msg.LOG_SKIP_FAILED_NO_MUSIC.format(user=user, channel=channel))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_SKIP_SONG))
            return

        song = self.current_song[0]
        title = song.get("title") or "Unknown title"
        source = song.get("source") or ""
        
        vc.stop()
        await ctx.send(embed=discord.Embed(description=msg.SKIP_SONG.format(title=title, source=source)))            

        logger.info(
            msg.LOG_SONG_SKIPPED.format(
                title=title, 
                user=user, 
                guild=ctx.guild.name
            )
        )


    @commands.command(name="queue", aliases=["q"], help=msg.HELP_MESSAGES['queue'], usage=msg.HELP_USAGES['queue'])
    async def queue(self, ctx):
        
        # Handle case no music in queue:
        if not self.current_song and not self.music_queue:
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_EMPTY))
            logger.info(msg.LOG_QUEUE_EMPTY.format(channel=ctx.channel.name))
            return
        
        vc = self.get_vc()
        channel_name = vc.channel.name if vc is not None and vc.channel is not None else "Not connected"

        data = {
            "time_label": "Estimated Total Playtime",
            "time": seconds_to_time_format(self.queue_duration),
            "thumbnail": ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None,
            "fields": [],
        }


        if self.current_song is not None:
            song = self.current_song[0]
            title = song.get("title") or "Unknown title"
            source = song.get("source") or ""
            description = (
                f"**Now playing**\n"
                f"[{title}]({source})" if source else f"**Now playing**\n{title}"
            )
            description = msg.NOW_PLAYING.format(
                title=title,
                source=source
            )        
        else:
            description = "Nothing currently playing."


        for idx, song_info in enumerate(self.music_queue, start=1):
            song = song_info[0]
            title = song.get("title") or "Unknown title"

            data['fields'].append({
                'label': "",
                'item': f"**{idx}.** {title}",
            })

        pagination_view = PaginationView(
            data=data,
            title=msg.QUEUE_STATUS.format(channel_name=channel_name),
            description=description,
            timeout=None
        )

        await pagination_view.send(ctx)
        
        number_of_songs = len(self.music_queue) + (1 if self.current_song else 0)

        logger.info(
            msg.LOG_QUEUE_DISPLAYED.format(
                channel=ctx.channel.name, 
                number_of_songs=number_of_songs
            )
        )


    @commands.command(name="playing", aliases=["np"], help=msg.HELP_MESSAGES['playing'], usage=msg.HELP_USAGES['playing'])
    async def playing(self, ctx):
        if self.current_song is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PLAYING))
            return 
        
        song = self.current_song[0]
        
        title = song.get("title") or "Unknown title"
        source = song.get("source") or ""
        
        await ctx.send(embed=discord.Embed(description=msg.PLAYING.format(title=title, source=source)))
        return
        

    @commands.command(name="remove", aliases=["rm"], help=msg.HELP_MESSAGES['remove'], usage=msg.HELP_USAGES['remove'])
    async def remove(self, ctx, *args):
        user = ctx.author.name

        if not self.music_queue:
            logger.warning(msg.LOG_REMOVE_FAILED_NO_QUEUE.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_QUEUE_EMPTY))
            return
        
        if not args:
            index = len(self.music_queue) - 1
        else:
            try:
                position = int(args[0])
            except ValueError:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_INDEX))
                return 
            
            if position < 1 or position > len(self.music_queue):
                await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_INDEX))

            index = position - 1

        song = self.music_queue.pop(index)[0]
        duration = song.get("duration") or 0
        title = song.get("title") or "Unknown title"

        self.queue_duration = max(0, self.queue_duration - duration)

        await ctx.send(embed=discord.Embed(description=msg.SONG_REMOVED.format(title=title)))
        
        logger.info(
            msg.LOG_REMOVE_LAST_EXECUTED.format(index=index + 1, user=user)
            if not args
            else msg.REMOVED_QUEUE_INDEX.format(index = index + 1))
        
    @commands.command(name="clear", aliases=["c", "bin"], help=msg.HELP_MESSAGES['clear'], usage=msg.HELP_USAGES['clear'])
    async def clear(self, ctx):
        vc = self.get_vc()
        user = ctx.author.name

        had_music = self.current_song is not None or bool(self.music_queue)

        self.music_queue.clear()
        self.current_song = None
        self.queue_duration = 0

        if vc is not None and (vc.is_playing() or vc.is_paused()):
            vc.stop()

        if not had_music:
            logger.info(msg.LOG_QUEUE_EMPTY.format(channel=ctx.channel.name))
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_EMPTY))
            return

        logger.info(msg.LOG_CLEAR_EXECUTED.format(user=user))
        await ctx.send(embed=discord.Embed(description=msg.QUEUE_CLEARED))


    @commands.command(name="stop", aliases=["disconnect"], help=msg.HELP_MESSAGES['stop'], usage=msg.HELP_USAGES['stop'])
    async def stop(self, ctx):
        vc = self.get_vc()
        # Clear the current song and the music queue
        if self.current_song or self.music_queue:
            logger.info(msg.LOG_STOP_EXECUTED)

            self.music_queue.clear()
            self.current_song = None
            self.queue_duration = 0     
        

        if vc:
            await vc.disconnect()
            self.vc = None
        logger.info(msg.LOG_STOP_EXECUTED.format(channel=ctx.author.voice.channel.name, user=ctx.author.name))


    @commands.command(name="status", aliases=["stat"], help=msg.HELP_MESSAGES['status'], usage=msg.HELP_USAGES['status'])
    async def status(self, ctx):
        songs = []
        for i in range(len(self.music_queue)):
            songs.append(self.music_queue[i][0]['title'])        
        
        vc = self.get_vc()
        if vc is None:
            return
        
        status_description = (    
            f"Playing: {vc.is_playing()}\n"
            f"Paused: {vc.is_paused()}\n"
            f"Current Song: {self.current_song[0].get("title") or "Unknown" if self.current_song else None}\n"           # | Not used, do !queue instead
            # f"Queue: {', '.join(songs)}\n"  # Join the song URLs with a comma and a space
            f"Queue Duration: {self.queue_duration}\n"
            f"Voice Channel: {self.vc.channel.name if self.vc and vc.is_connected() else 'Not connected'}"
        )
        
        embed = discord.Embed(
            title=":gear: Bot Status :gear:",
            description=status_description,
            color=discord.Color.blue()
        )
        # logger.info(msg.LOG_STATUS)
        await ctx.send(embed=embed)


            