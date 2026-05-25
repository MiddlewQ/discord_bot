import discord
import asyncio
from discord.ext import commands
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError
from enum import StrEnum, auto
from dataclasses import dataclass

from src.utils.logging_config import *
import src.utils.message as msg
from src.utils.time_convertion import *
from src.utils.partionation import PaginationView

logger = logging.getLogger("audio")

@dataclass
class QueueEntry:
    track: dict

class PlaybackState(StrEnum):
    DISCONNECTED = auto()
    IDLE = auto()
    PLAYING = auto()
    PAUSED = auto()

class TimeoutReason(StrEnum):
    NO_HUMANS = auto()
    IDLE = auto()
    PAUSED = auto()

@dataclass(frozen=True)
class VoiceContext:
    state: PlaybackState
    vc: discord.VoiceClient | None
    user_channel: discord.VoiceChannel | discord.StageChannel | None

@dataclass(frozen=True)
class TimeoutPolicy:
    seconds: int
    discord_message: str
    log_message: str

TIMEOUT_POLICIES = {
    TimeoutReason.NO_HUMANS: TimeoutPolicy(
        seconds = 120,
        discord_message=msg.TIMEOUT_NO_HUMANS,
        log_message=msg.LOG_TIMEOUT_NO_HUMANS,
    ),
    TimeoutReason.IDLE: TimeoutPolicy(
        seconds=600,
        discord_message=msg.TIMEOUT_IDLE,
        log_message=msg.LOG_TIMEOUT_IDLE,
    ),
    TimeoutReason.PAUSED: TimeoutPolicy(
        seconds=1800,
        discord_message=msg.TIMEOUT_PAUSED,
        log_message=msg.LOG_TIMEOUT_PAUSED
    ),
}

class AudioCog(commands.Cog):

    # 1. Setup & configuration
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        self.current_track: QueueEntry | None = None
        self.track_queue: list[QueueEntry] = []
        self.queued_duration_seconds: int = 0
        self.logger = logger

        self.timeout_task = None
        
        self.YDL_OPTIONS = {"format": "bestaudio[ext=m4a]/bestaudio/best", 
                            "noplaylist": True,
                            "quiet": True,}
        self.FFMPEG_OPTIONS = {'options':        '-vn', 
                               'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5' }

        self.session_text_channel: discord.TextChannel | discord.Thread | None = None
        self.vc = None

        self.ytdl = YoutubeDL(self.YDL_OPTIONS) # type: ignore

        self.logger.info("AudioCog initialized successfully.")

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    # 2. State helpers
    def get_vc(self) -> discord.VoiceClient | None:
        if self.vc is None or not self.vc.is_connected():
            return None
        return self.vc

    def playback_state(self) -> PlaybackState:
        vc = self.get_vc()
        if vc is None:
            return PlaybackState.DISCONNECTED
        if vc.is_paused():
            return PlaybackState.PAUSED
        
        if vc.is_playing():
            return PlaybackState.PLAYING

        return PlaybackState.IDLE

    async def ensure_voice_client(self, channel):
        vc = self.get_vc()
        
        if vc is None:
            vc = await channel.connect()
            self.vc = vc
            return vc
        
        if vc.channel != channel:
            await vc.move_to(channel)
        
        return vc

    async def prepare_voice_for_playback(self, ctx, channel) -> bool:
        try:
            await self.ensure_voice_client(channel)
        except Exception:
            logger.exception("Failed to connect or move to voice channel.")
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_CONNECT_TO_VOICE_CHANNEL))
            return False
        return True

    async def reject_wrong_text_channel(self, ctx) -> bool:
        if self.playback_state() not in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            return False
        
        if self.session_text_channel is None:
            logger.warning("Playback active without a session text channel. Locking to current channel.")
            self.session_text_channel = ctx.channel
            return False
        
        if ctx.channel == self.session_text_channel:
            return False
        
        logger.info(msg.LOG_COMMAND_FAILED_DIFFERENT_TEXT_CHANNEL.format(
            user=ctx.author.name,
            command=ctx.command.name if ctx.command else "unknown",
            current_channel=ctx.channel.name,
            session_channel=self.session_text_channel.name,
        ))
        return True

    def get_voice_context(self, ctx) -> VoiceContext:
        state = self.playback_state()
        vc = self.get_vc()

        user_voice = ctx.author.voice
        user_channel: discord.VoiceChannel | discord.StageChannel | None = user_voice.channel if user_voice and user_voice.channel else None

        return VoiceContext(
            state=state,
            vc=vc,
            user_channel=user_channel,
        )

    def _clear_playback_state(self):
        self.track_queue.clear()
        self.current_track = None
        self.queued_duration_seconds = 0

    def _reset_voice_session(self):
        self.cancel_timeout()
        self._clear_playback_state()
        self.vc = None
        self.session_text_channel = None

    def subtract_track_duration(self, queue_entry: QueueEntry):
        duration = queue_entry.track.get("duration") or 0
        self.queued_duration_seconds = max(0, self.queued_duration_seconds - duration)

    async def cleanup_voice(self, message: str):
        text_channel = self.session_text_channel
        vc = self.get_vc()

        # Mark internal state as gone before Discord fires voice-state events.
        self._reset_voice_session()

        if vc is not None:
            await vc.disconnect()

        logger.info(f"Disconnected from voice.")

        if text_channel is not None:
            await text_channel.send(embed=discord.Embed(description=message))

        
    # 3. Embed / yt-dlp helders
    def build_queued_track_embed(self, track, requester):
        embed = discord.Embed(
            title="",
            color=discord.Color.blue(),
            type='rich'
        )
        bot_user = self.bot.user
        icon_url = bot_user.display_avatar.url if bot_user is not None else None
        duration = track.get("duration") or 0
        time_until_played = max(0, self.queued_duration_seconds - duration)
        fields = [
            # Name, value, inline
            ("Track", f"[{track['title']}]({track['webpage_url']})", False),
            ("", "", False),
            ("Estimated time until played", f"{seconds_to_time_format(time_until_played)}", True),
            ("Track length", f"{seconds_to_time_format(duration)}", True),
            ("", "", True),
            ("Position in upcoming", f"{len(self.track_queue) if len(self.track_queue) > 0 else 'Next'}", True),
            ("Position in queue", f"{len(self.track_queue)+1}", True),
            ("", "", True)
        ]

        for name, val, inline in fields:
            embed.add_field(name=name, value=val, inline=inline)   

        embed.set_author(icon_url=icon_url, name="Added track")
        thumbnail = track.get("thumbnail")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        embed.set_footer(icon_url=requester.avatar.url, text=f"requested by {str(requester).capitalize()}") 
        return embed

    async def search_youtube(self, query: str) -> tuple[dict | None, str | None]:
        loop = asyncio.get_running_loop()

        is_url = query.startswith("http")
        search_query = query if is_url else f"ytsearch1:{query}"

        try:
            info = await loop.run_in_executor(
                None,
                lambda: self.ytdl.extract_info(search_query, download=False)
            )

        except (DownloadError, ExtractorError) as e:
            error_text = str(e).lower()

            if "this video is not available" in error_text:
                logger.warning(msg.LOG_YTDLP_FAILED_UNAVAILABLE.format(query=query, error=e))
                return None, msg.PLAY_FAIL_VIDEO_UNAVAILABLE

            if (
                "sign in to confirm your age" in error_text
                or "age-restricted" in error_text
                or "this video may be inappropriate" in error_text
            ):
                logger.warning(msg.LOG_YTDLP_FAILED_AGE_RESTRICTED.format(query=query, error=e))
                return None, msg.PLAY_FAIL_VIDEO_AGE_RESTRICTED

            if (
                "no supported javascript runtime" in error_text
                or ("javascript runtime" in error_text and "deno" in error_text)
            ):
                logger.warning(msg.LOG_YTDLP_FAILED_RUNTIME.format(query=query, error=e))
                return None, msg.PLAY_FAIL_YTDLP_RUNTIME

            logger.warning(msg.LOG_YTDLP_FAILED_EXTRACTION.format(query=query, error=e))
            return None, msg.PLAY_FAIL_YTDLP_ERROR
        except Exception:
            logger.exception(msg.LOG_YTDLP_FAILED_UNEXPECTED.format(query=query))
            return None, msg.PLAY_FAIL_YTDLP_ERROR


        if not isinstance(info, dict):
            logger.warning(msg.LOG_YTDLP_RESULT_INVALID.format(query=query,result_type=type(info).__name__,))
            return None, msg.PLAY_FAIL_VIDEO_NOT_FOUND

        entries = info.get("entries")

        if isinstance(entries, list):
            if not entries:
                logger.warning(msg.LOG_YTDLP_RESULT_EMPTY.format(query=query))
                return None, msg.PLAY_FAIL_VIDEO_NOT_FOUND

            maybe_entry = entries[0]
        else:
            maybe_entry = info 

        if not isinstance(maybe_entry, dict):
            logger.warning(msg.LOG_YTDLP_ENTRY_INVALID.format(query=query, entry_type=type(maybe_entry).__name__))
            return None, msg.PLAY_FAIL_VIDEO_NOT_FOUND

        entry = maybe_entry 

        webpage_url = entry.get('webpage_url') or entry.get("original_url")
        if not isinstance(webpage_url, str) or not webpage_url:
            logger.warning(msg.LOG_YTDLP_ENTRY_MISSING_URL.format(query=query))
            return None, msg.PLAY_FAIL_VIDEO_NOT_FOUND

        thumbnail = entry.get("thumbnail")
        if not thumbnail:
            thumbnails = entry.get("thumbnails") or []
            if isinstance(thumbnails, list) and thumbnails:
                first = thumbnails[0]
                last = thumbnails[-1]

                first_url = first.get("url") if isinstance(first, dict) else None
                last_url = last.get("url") if isinstance(last, dict) else None

                thumbnail = first_url or last_url

        return {
            'webpage_url': webpage_url,
            'title': entry.get('title'),
            'thumbnail': thumbnail,
            'duration': entry.get('duration') or 0,
        }, None

    # 4. Core playback internals
    async def start_playback(self, ctx):
        """Start playback if the bot is not already playing."""
        state = self.playback_state()
        
        if state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            logger.debug(msg.LOG_PLAY_NEXT_IGNORE_ALREADY_PLAYING.format(state=state))
            return
        
        await self.play_next_track(ctx=ctx)
        return
    
    async def play_next_track(self, ctx=None, error=None):
        if error is not None:
            logger.warning(f"Playback ended with error: {error}")

        if self.current_track is not None:
            self.subtract_track_duration(self.current_track)
            self.current_track = None

        while self.track_queue:
            vc = self.get_vc()
            if vc is None:
                logger.warning("Cannot play next track because the bot is not connected. Clearing playback state.")
                self._reset_voice_session()
                return
            queue_entry = self.track_queue.pop(0)
            
            started = await self.try_play_track(vc, queue_entry, ctx)
            
            if started:
                return
             
            self.subtract_track_duration(queue_entry)

        self.current_track = None
        self.queued_duration_seconds = 0
        self.session_text_channel = None

        if self.get_vc() is not None:
            self.start_timeout(reason=TimeoutReason.IDLE)

    async def try_play_track(self, vc: discord.VoiceClient, queue_entry: QueueEntry, ctx=None) -> bool:
        track = queue_entry.track
        
        webpage_url = track.get("webpage_url")

        if not isinstance(webpage_url, str) or not webpage_url:
            logger.info(f"Skipping queue item with invalid source: {track}")

            if ctx is not None:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYBACK))
            return False
        
        try:
            data = await self.extract_audio_info(webpage_url)

            stream_url = data.get("url")
            title= data.get("title") or "Unknown title"

            if not isinstance(stream_url, str) or not stream_url:
                raise ValueError(f"No valid stream URL found for {title}")

            audio_source = discord.FFmpegPCMAudio(
                source=stream_url,
                executable="ffmpeg",
                options=self.FFMPEG_OPTIONS["options"],
                before_options=self.FFMPEG_OPTIONS["before_options"],
            )

            vc.play(
                source=audio_source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next_track(error=e),
                    self.bot.loop,
                )
            )

            self.current_track = queue_entry
            self.cancel_timeout()

            logger.info(msg.LOG_PLAY_NEXT_REQUEST_EXECUTED.format(title=title))
            return True        

        except Exception:
            logger.exception("Failed to play track.")

            if ctx is not None:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_PLAYBACK))
            
            return False

    async def extract_audio_info(self, webpage_url: str):
        loop = asyncio.get_running_loop()

        data = await loop.run_in_executor(
            None,
            lambda: self.ytdl.extract_info(url=webpage_url, download=False),
        )

        if not isinstance(data, dict):
            raise ValueError("yt-dlp returned invalid data")
        
        return data

    async def resolve_queue_entry(self, ctx, query: str) -> QueueEntry | None:

        track, error_message = await self.search_youtube(query)
        
        if track is None:
            await ctx.send(embed=discord.Embed(description=error_message or msg.PLAY_FAIL_VIDEO_NOT_FOUND))
            return None
        
        title = track.get("title") or "Unknown title"
        webpage_url = track.get("webpage_url")
        duration = track.get("duration") or 0

        if not isinstance(webpage_url, str) or not webpage_url:
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_VIDEO_NOT_FOUND))
            logger.info(msg.LOG_PLAY_FAILED_NOT_FOUND.format(query=query, user=ctx.author.name))
            return None

        if duration > 1200:
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_VIDEO_TOO_LONG.format(minutes=1200/60)))
            logger.info(msg.LOG_PLAY_FAILED_TOO_LONG.format(query=query, user=ctx.author.name))
            return None

        return QueueEntry(track=track)       
    
    def queue_track(self, queue_entry: QueueEntry):
        duration = queue_entry.track.get("duration") or 0
        self.track_queue.append(queue_entry)
        self.queued_duration_seconds += duration

        title = queue_entry.track.get("title") or "Unknown title"
        webpage_url = queue_entry.track.get("webpage_url") or ""

        logger.info(msg.LOG_PLAY_TRACK_QUEUED.format(title=title, webpage_url=webpage_url))


    # 5. Idle / cleanup internals
    def start_timeout(self, reason: TimeoutReason):
        policy = TIMEOUT_POLICIES[reason]
        self.cancel_timeout()
    
        logger.info(msg.LOG_TIMEOUT_START.format(reason=reason, seconds=policy.seconds))
        
        self.timeout_task = asyncio.create_task(
            self.disconnect_after_timeout(reason)
        )

    def cancel_timeout(self):
        if self.timeout_task is None:
            return 

        task = self.timeout_task
        self.timeout_task = None

        if task is not asyncio.current_task():
            task.cancel()

    async def disconnect_after_timeout(self, reason: TimeoutReason):
        policy = TIMEOUT_POLICIES[reason]

        try:
            await asyncio.sleep(policy.seconds)

            vc = self.get_vc()
            channel_name = vc.channel.name if vc is not None and vc.channel else "unknown"

            logger.info(policy.log_message.format(channel=channel_name))
            await self.cleanup_voice(policy.discord_message)
        except asyncio.CancelledError:
            pass


    # 6. Listeners
    @commands.Cog.listener()
    async def on_command(self, ctx):
        logger.info(f"{ctx.command.name.capitalize()} command requested: User {ctx.author.name} in {ctx.channel.name}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if self.bot.user is not None and member.id == self.bot.user.id:
            if before.channel is not None and after.channel is None:
                if self.vc is None and self.session_text_channel is None:
                    return

                logger.warning("Bot was disconnected from voice. Clearing playback state.")
                
                text_channel = self.session_text_channel
                self._reset_voice_session()

                if text_channel is not None:
                    await text_channel.send(embed=discord.Embed(description=msg.DISCONNECTED_FROM_VOICE))

            return

        vc = self.get_vc()
        if vc is None or vc.channel is None:
            return
        
        if before.channel != vc.channel and after.channel != vc.channel:
            return
        
        humans = [m for m in vc.channel.members if not m.bot]

        state = self.playback_state()

        if len(humans) == 0:
            self.start_timeout(TimeoutReason.NO_HUMANS)
            return 

        if state == PlaybackState.PLAYING:
                self.cancel_timeout()
        elif state == PlaybackState.PAUSED:
            self.start_timeout(TimeoutReason.PAUSED)
        elif state == PlaybackState.IDLE:
            self.start_timeout(TimeoutReason.IDLE)

    
    # 7. Commands
    @commands.command(name="join", aliases=['connect'], help=msg.HELP_MESSAGES['join'], usage=msg.HELP_USAGES['join'])
    async def join(self, ctx):
        if await self.reject_wrong_text_channel(ctx):
            return
        
        voice = self.get_voice_context(ctx)
        user = ctx.author
        
        if voice.user_channel is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            logger.info(msg.LOG_JOIN_FAILED_USER_ABSENT.format(user=user.name))
            return
        
        old_channel_name: str | None = None

        if voice.vc is not None:
            if voice.user_channel == voice.vc.channel:
                if voice.state == PlaybackState.IDLE:
                    self.start_timeout(TimeoutReason.IDLE)
                await ctx.send(embed=discord.Embed(description=msg.JOIN_FAIL_SAME_CHANNEL))
                logger.info(msg.LOG_JOIN_FAILED_USER_CHANNEL_SAME.format(user=user.name, channel=voice.vc.channel.name))
                return
            if voice.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
                await ctx.send(embed=discord.Embed(description=msg.JOIN_FAIL_PLAYING_OTHER_CHANNEL))
                logger.info(msg.LOG_JOIN_FAILED_PLAYBACK_OTHER.format(user=user.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
                return
            
            # Bot is idle in another channel: move
            old_channel_name = voice.vc.channel.name


        try:
            await self.ensure_voice_client(voice.user_channel)
        except Exception:
            logger.exception("Failed to connect to voice channel.")
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_CONNECT_TO_VOICE_CHANNEL))
            return 
        
        self.start_timeout(TimeoutReason.IDLE)

        if old_channel_name is None:
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_CONNECTED.format(channel=voice.user_channel.name)))
            logger.info(msg.LOG_JOIN_CHANNEL_CONNECT.format(user=user.name, channel=voice.user_channel.name))
        else: 
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_MOVED.format(channel=voice.user_channel.name)))
            logger.info(msg.LOG_JOIN_CHANNEL_MOVE.format(user=user.name, old=old_channel_name, new=voice.user_channel.name))


    @commands.command(name="play", aliases=["p", "pl"], help=msg.HELP_MESSAGES['play'], usage=msg.HELP_USAGES['play'])
    async def play(self, ctx, *args):

        if not args:
            logger.info(msg.LOG_PLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_NO_ARGS))
            return
        
        
        voice = self.get_voice_context(ctx)
        
        if voice.user_channel is None:
            logger.info(msg.LOG_PLAY_FAILED_USER_NOT_CONNECTED.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            return

        should_start_after_queue = False
        should_connect_or_move = False

        if voice.state in (PlaybackState.DISCONNECTED, PlaybackState.IDLE):
            should_start_after_queue = True
            should_connect_or_move = voice.vc is None or voice.vc.channel != voice.user_channel
        elif voice.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            if await self.reject_wrong_text_channel(ctx):
                return

            if voice.vc is None:
                logger.warning("Playback state was %s but voice client was missing", voice.state)
                await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
                return

            if voice.user_channel != voice.vc.channel:
                await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_QUEUE_FROM_OTHER_CHANNEL.format(channel=voice.vc.channel.name)))
                logger.info(msg.LOG_PLAY_FAILED_USER_CHANNEL_OTHER.format(user=ctx.author.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
                return 

        query = " ".join(args)

        queue_entry = await self.resolve_queue_entry(ctx, query)
        if queue_entry is None:
            return

        track = queue_entry.track
        title = track.get("title") or "Unknown title"
        webpage_url = track.get("webpage_url") or ""        

        if should_connect_or_move:
            ok = await self.prepare_voice_for_playback(ctx, voice.user_channel)
            if not ok:
                return

        self.queue_track(queue_entry=queue_entry)
        
        if should_start_after_queue:
            self.session_text_channel = ctx.channel
            await ctx.send(embed=discord.Embed(description=msg.START_PLAYBACK.format(title=title, webpage_url=webpage_url)))
            await self.start_playback(ctx)
        else:
            await ctx.send(embed=self.build_queued_track_embed(track, ctx.author))


    @commands.command(name="multiplay", aliases=["mp", "mplay", "mb"], help=msg.HELP_MESSAGES['multiplay'], usage=msg.HELP_USAGES['multiplay'])
    async def multiplay(self, ctx, *args):
        if await self.reject_wrong_text_channel(ctx):
            return

        if not args:
            logger.info(msg.LOG_MULTIPLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_NO_ARGS))
            return 
        
        voice = self.get_voice_context(ctx)

        if voice.user_channel is None:
            logger.info(msg.LOG_PLAY_FAILED_USER_NOT_CONNECTED.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            return
        
        should_start_after_queue = False
        should_connect_or_move = False
        if voice.state in (PlaybackState.DISCONNECTED, PlaybackState.IDLE):
            should_start_after_queue = True
            should_connect_or_move = voice.vc is None or voice.vc.channel != voice.user_channel

        elif voice.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            if voice.vc is None:
                logger.warning("Playback state was %s because client was missing", voice.state)
                await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
                return
            
            if voice.user_channel != voice.vc.channel:
                await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_QUEUE_FROM_OTHER_CHANNEL.format(channel=voice.vc.channel.name)))
                logger.info(msg.LOG_PLAY_FAILED_USER_CHANNEL_OTHER.format(user=ctx.author.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name,))
                return
        
        query = " ".join(args)
        
        searches = [
            search.strip() 
            for search in query.split('|')
            if search.strip()
        ]
        
        if not searches:
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_NO_ARGS))
            return 
        
        add_max = 20
        if len(searches) > add_max:
            await ctx.send(embed=discord.Embed(description=msg.MULTIPLAY_MAX_TRACKS.format(number=add_max)))
            searches = searches[:add_max]

        queued_entries: list[QueueEntry] = []
        for search in searches:
            queue_entry = await self.resolve_queue_entry(ctx, search)
            if queue_entry is None:
                continue

            queued_entries.append(queue_entry)

        queued_count = len(queued_entries) 

        if queued_count == 0:
            return

        if should_connect_or_move:
            ok = await self.prepare_voice_for_playback(ctx, voice.user_channel)
            if not ok:
                return
        
        for queue_entry in queued_entries:
            self.queue_track(queue_entry=queue_entry)
            await ctx.send(embed=self.build_queued_track_embed(queue_entry.track, ctx.author))

        if should_start_after_queue:
            self.session_text_channel = ctx.channel
            await ctx.send(embed=discord.Embed(description=msg.MULTIPLAY_START_PLAYBACK.format(number=queued_count)))
            await self.start_playback(ctx)
        else:
            await ctx.send(embed=discord.Embed(description=msg.MULTIPLAY_QUEUE_TRACKS.format(number=queued_count)))
            
        logger.info(msg.LOG_MULTIPLAY_EXECUTED.format(number_of_tracks=queued_count))


    @commands.command(name="pause", help="Pauses the current track being played.", usage="!pause")
    async def pause(self, ctx):
        if await self.reject_wrong_text_channel(ctx):
            return

        voice = self.get_voice_context(ctx)
        user = ctx.author

        if voice.vc is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
            logger.info(msg.LOG_PAUSE_FAILED_BOT_ABSENT.format(user=user.name))
            return 
        
        if voice.user_channel is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            logger.info(msg.LOG_PAUSE_FAILED_USER_ABSENT.format(user=user.name, channel=voice.vc.channel.name))
            return 

        if voice.user_channel != voice.vc.channel:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_DIFFERENT_CHANNEL))
            logger.info(msg.LOG_PAUSE_FAILED_DIFFERENT_CHANNEL.format(user=user.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
            return 

        if voice.state == PlaybackState.IDLE:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PLAYING))
            logger.info(msg.LOG_PAUSE_FAILED_NOT_PLAYING.format(user=user.name))
            return 

        if voice.state == PlaybackState.PAUSED:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_ALREADY_PAUSED))
            logger.info(msg.LOG_PAUSE_FAILED_ALREADY_PAUSED.format(user=user.name)) 
            return 
        
        voice.vc.pause()

        await ctx.send(embed=discord.Embed(description=msg.PAUSED))
        logger.info(msg.LOG_PAUSE_EXECUTED.format(user=user.name))
        self.start_timeout(TimeoutReason.PAUSED)

        

    @commands.command(name = "resume", aliases=["r"], help=msg.HELP_MESSAGES['resume'], usage=msg.HELP_USAGES['resume'])
    async def resume(self, ctx):
        if await self.reject_wrong_text_channel(ctx):
            return

        user = ctx.author

        voice = self.get_voice_context(ctx)

        if voice.vc is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
            logger.info(msg.LOG_RESUME_FAILED_BOT_ABSENT.format(user=user.name))
            return 
        
        if voice.user_channel is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            logger.info(msg.LOG_RESUME_FAILED_USER_ABSENT.format(user=user.name, channel=voice.vc.channel.name))
            return 

        if voice.user_channel != voice.vc.channel:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_DIFFERENT_CHANNEL))
            logger.info(msg.LOG_RESUME_FAILED_DIFFERENT_CHANNEL.format(user=user.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
            return 

        if voice.state == PlaybackState.PLAYING:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_ALREADY_PLAYING))
            logger.info(msg.LOG_RESUME_FAILED_ALREADY_PLAYING.format(user=ctx.author.name))
            return

        if voice.state != PlaybackState.PAUSED:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PAUSED))
            logger.info(msg.LOG_RESUME_FAILED_NOT_PAUSED.format(user=ctx.author.name))
            return 
        
        voice.vc.resume()
        self.cancel_timeout()

        await ctx.send(embed=discord.Embed(description=msg.RESUMED))
        logger.info(msg.LOG_RESUME_EXECUTED.format(user=ctx.author.name))


    @commands.command(name="skip", aliases=["s"], help=msg.HELP_MESSAGES['skip'], usage=msg.HELP_USAGES['skip'])
    async def skip(self, ctx):
        if await self.reject_wrong_text_channel(ctx):
            return

        user = ctx.author
        voice = self.get_voice_context(ctx)

        if voice.vc is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
            logger.info(msg.LOG_SKIP_FAILED_BOT_ABSENT.format(user=user.name))
            return 
        

        if voice.user_channel is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            logger.info(msg.LOG_SKIP_FAILED_USER_ABSENT.format(user=user.name, channel=voice.vc.channel.name))
            return 

        if voice.user_channel != voice.vc.channel:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_DIFFERENT_CHANNEL))
            logger.info(msg.LOG_SKIP_FAILED_DIFFERENT_CHANNEL.format(user=user.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
            return 

        if voice.state not in (PlaybackState.PLAYING, PlaybackState.PAUSED) or self.current_track is None:
            logger.info(msg.LOG_SKIP_FAILED_NO_AUDIO.format(user=user.name, channel=voice.vc.channel.name))
            await ctx.send(embed=discord.Embed(description=msg.SKIP_FAIL_NOTHING_TO_SKIP))
            return

        track = self.current_track.track
        title = track.get("title") or "Unknown title"
        webpage_url = track.get("webpage_url") or ""
        
        voice.vc.stop()

        await ctx.send(embed=discord.Embed(description=msg.SKIP_TRACK.format(title=title, webpage_url=webpage_url)))            
        logger.info(msg.LOG_TRACK_SKIPPED.format(title=title, user=user.name))


    @commands.command(name="queue", aliases=["q"], help=msg.HELP_MESSAGES['queue'], usage=msg.HELP_USAGES['queue'])
    async def queue(self, ctx):
        
        if not self.current_track and not self.track_queue:
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_EMPTY))
            logger.info(msg.LOG_QUEUE_EMPTY.format(channel=ctx.channel.name))
            return
        
        vc = self.get_vc()
        channel_name = vc.channel.name if vc is not None and vc.channel is not None else "Not connected"

        data = {
            "time_label": "Estimated Total Playtime",
            "time": seconds_to_time_format(self.queued_duration_seconds),
            "thumbnail": ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None,
            "fields": [],
        }


        if self.current_track is not None:
            track = self.current_track.track
            title = track.get("title") or "Unknown title"
            webpage_url = track.get("webpage_url") or "Unknown url"
            description = msg.QUEUE_START_PLAYBACK.format(
                title=title,
                webpage_url=webpage_url
            )        
        else:
            description = "Nothing currently playing."


        for idx, queue_entry in enumerate(self.track_queue, start=1):
            track = queue_entry.track
            title = track.get("title") or "Unknown title"

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
        
        number_of_tracks = len(self.track_queue) + (1 if self.current_track else 0)

        logger.info(
            msg.LOG_QUEUE_DISPLAYED.format(
                channel=ctx.channel.name, 
                number_of_tracks=number_of_tracks
            )
        )


    @commands.command(name="playing", aliases=["np"], help=msg.HELP_MESSAGES['playing'], usage=msg.HELP_USAGES['playing'])
    async def playing(self, ctx):
        if self.current_track is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PLAYING))
            return 
        
        track = self.current_track.track
        title = track.get("title") or "Unknown title"
        webpage_url = track.get("webpage_url") or "Unknown url"
        thumbnail = track.get("thumbnail") 
        embed = discord.Embed(description=msg.PLAYING.format(title=title, webpage_url=webpage_url))
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        await ctx.send(embed=embed)

        return
        

    @commands.command(name="remove", aliases=["rm"], help=msg.HELP_MESSAGES['remove'], usage=msg.HELP_USAGES['remove'])
    async def remove(self, ctx, *args):
        if await self.reject_wrong_text_channel(ctx):
            return

        if not self.track_queue:
            logger.info(msg.LOG_REMOVE_FAILED_NO_QUEUE.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_QUEUE_EMPTY))
            return
        
        
        voice = self.get_voice_context(ctx)
        if voice.vc is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
            logger.info(msg.LOG_REMOVE_FAILED_BOT_ABSENT.format(user=ctx.author.name))
            return

        if voice.user_channel is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            logger.info(msg.LOG_REMOVE_FAILED_USER_ABSENT.format(user=ctx.author.name, channel=voice.vc.channel.name,))
            return

        if voice.user_channel != voice.vc.channel:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_DIFFERENT_CHANNEL))
            logger.info(msg.LOG_REMOVE_FAILED_DIFFERENT_CHANNEL.format(user=ctx.author.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name,)) 
            return

        if args:
            try:
                position = int(args[0])
            except ValueError:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_INDEX))
                return 
            
            if position < 1 or position > len(self.track_queue):
                await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_INDEX))
                return 
            index = position - 1

        else:
            index = len(self.track_queue) - 1

        queue_entry = self.track_queue.pop(index)
        track = queue_entry.track
        title = track.get("title") or "Unknown title"

        self.subtract_track_duration(queue_entry)
        embed = discord.Embed(description=msg.TRACK_REMOVED.format(title=title, index=index + 1))

        thumbnail = track.get("thumbnail")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        await ctx.send(embed=embed)
        
        logger.info(
            msg.LOG_REMOVE_LAST_EXECUTED.format(index=index + 1, user=ctx.author.name)
            if not args
            else msg.LOG_REMOVE_EXECUTED.format(index=index + 1, user=ctx.author.name)
        )


    @commands.command(name="clear", aliases=["c", "bin"], help=msg.HELP_MESSAGES['clear'], usage=msg.HELP_USAGES['clear'])
    async def clear(self, ctx):
        if await self.reject_wrong_text_channel(ctx):
            return

        voice = self.get_voice_context(ctx)

        if self.current_track is None and not self.track_queue:
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_EMPTY))
            logger.info(msg.LOG_QUEUE_EMPTY.format(channel=ctx.channel.name))
            return

        if voice.vc is None:
            # If disconnected but stale queue exists, clearing ok
            self._clear_playback_state()
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_CLEARED))
            logger.info(msg.LOG_CLEAR_EXECUTED.format(user=ctx.author.name))
            return
        
        if voice.user_channel is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            logger.info(msg.LOG_CLEAR_FAILED_USER_ABSENT.format(user=ctx.author.name, channel=voice.vc.channel.name))
            return

        if voice.user_channel != voice.vc.channel:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_DIFFERENT_CHANNEL))
            logger.info(msg.LOG_CLEAR_FAILED_DIFFERENT_CHANNEL.format(user=ctx.author.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
            return 
        
        self._clear_playback_state()
        self.session_text_channel = None
        
        if voice.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            self.cancel_timeout()
            voice.vc.stop()
        elif voice.state == PlaybackState.IDLE:
            self.start_timeout(TimeoutReason.IDLE)

        await ctx.send(embed=discord.Embed(description=msg.QUEUE_CLEARED))
        logger.info(msg.LOG_CLEAR_EXECUTED.format(user=ctx.author.name))


    @commands.command(name="stop", aliases=["disconnect"], help=msg.HELP_MESSAGES['stop'], usage=msg.HELP_USAGES['stop'])
    async def stop(self, ctx):
        if await self.reject_wrong_text_channel(ctx):
            return

        voice = self.get_voice_context(ctx)

        if voice.vc is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
            logger.info(msg.LOG_STOP_FAILED_NOT_CONNECTED.format(user=ctx.author.name))
            return


        if voice.user_channel is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            logger.info(msg.LOG_STOP_FAILED_USER_ABSENT.format(user=ctx.author.name, channel=voice.vc.channel.name))
            return 
        
        if voice.user_channel != voice.vc.channel:
            await ctx.send(embed=discord.Embed(description=msg.STOP_FAIL_DIFFERENT_CHANNEL))
            logger.info(msg.LOG_STOP_FAILED_DIFFERENT_CHANNEL.format(user=ctx.author.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
            return
        
        
        await self.cleanup_voice(msg.STOP_BY_USER)
        
        logger.info(msg.LOG_STOP_EXECUTED.format(channel=voice.vc.channel.name, user=ctx.author.name))


    @commands.command(name="status", aliases=["stat"], help=msg.HELP_MESSAGES['status'], usage=msg.HELP_USAGES['status'])
    async def status(self, ctx):
        tracks = []
        for i in range(len(self.track_queue)):
            tracks.append(self.track_queue[i].track['title'])        
        
        vc = self.get_vc()

        voice = vc.channel.name if vc is not None and vc.is_connected() else None 
        text = self.session_text_channel.name if self.session_text_channel else None
        is_playing = vc.is_playing() if vc else False
        is_paused = vc.is_paused() if vc else False
            
        
        current_title = (
            self.current_track.track.get("title") or "Unknown"
            if self.current_track
            else None
        )

        status_description = (    
            f"Playing: {is_playing}\n"
            f"Paused: {is_paused}\n"
            f"Current Track: {current_title}\n"
            f"Queue: {', '.join(tracks)}\n"  # Join the song URLs with a comma and a space
            f"Queue Duration: {self.queued_duration_seconds}\n"
            f"Voice Channel: {voice}\n"
            f"Text Channel: {text}"
        )
        
        embed = discord.Embed(
            title=":gear: Bot Status :gear:",
            description=status_description,
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)



