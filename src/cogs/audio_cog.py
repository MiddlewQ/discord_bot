import discord
import asyncio
from dataclasses import dataclass
from enum import StrEnum, auto
from discord.ext import commands
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from src.bot.playback import AsyncioTimer, DiscordSessionNotifier, DiscordVoiceConnection
from src.audio.track import Track
from src.audio.voice_session import EndReason, PlaybackState, VoiceSession
from src.utils.logging_config import *
import src.utils.message as msg
from src.utils.time_convertion import *
from src.utils.partionation import PaginationView

logger = logging.getLogger("audio")

MAX_TRACK_SECONDS = 1200
MULTIPLAY_MAX_TRACKS = 8


@dataclass(frozen=True)
class VoiceContext:
    state: PlaybackState
    vc: discord.VoiceClient | None
    user_channel: discord.VoiceChannel | discord.StageChannel | None


class VoiceChannelReject(StrEnum):
    BOT_NOT_CONNECTED  = auto()
    USER_NOT_CONNECTED = auto()
    DIFFERENT_VOICE_CHANNEL = auto()


class AudioCog(commands.Cog):

    # 1. Setup & configuration
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        
        self.session = VoiceSession(DiscordSessionNotifier(bot), AsyncioTimer())
        self.logger = logger

        self.YDL_OPTIONS = {"format": "bestaudio[ext=m4a]/bestaudio/best",
                            "noplaylist": True,
                            "quiet": True,}

        self.ytdl = YoutubeDL(self.YDL_OPTIONS) # type: ignore

        self.logger.info("AudioCog initialized successfully.")

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    # Timeouts are held while any command runs, so the bot never leaves mid-command
    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        self.session.begin_request()

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        self.session.finish_request()

    # 2. State helpers
    def get_vc(self, guild: discord.Guild | None) -> discord.VoiceClient | None:
        """The guild's voice client, or None when the voice session is not connected."""
        if guild is None or self.session.state == PlaybackState.DISCONNECTED:
            return None

        vc = guild.voice_client
        return vc if isinstance(vc, discord.VoiceClient) else None

    async def ensure_voice_client(self, channel) -> discord.VoiceClient:
        existing_vc = channel.guild.voice_client

        if isinstance(existing_vc, discord.VoiceClient):
            if existing_vc.channel != channel:
                await existing_vc.move_to(channel)
            return existing_vc

        return await channel.connect()

    async def connect_session(self, ctx, channel) -> bool:
        """Connect or move to the voice channel and hand the connection to the voice session."""
        try:
            vc = await self.ensure_voice_client(channel)
        except Exception:
            logger.exception("Failed to connect or move to voice channel.")
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_CONNECT_TO_VOICE_CHANNEL))
            return False

        self.session.attach(DiscordVoiceConnection(vc), ctx.channel.id)
        return True

    async def reject_invalid_text_channel(self, ctx) -> bool:
        if self.session.accepts_commands_from(ctx.channel.id):
            return False

        # Only logged, no reply: replying in other text channels clutters them
        session_channel = self.bot.get_channel(self.session.text_channel_id or 0)

        logger.info(msg.LOG_COMMAND_FAILED_DIFFERENT_TEXT_CHANNEL.format(
            user=ctx.author.name,
            command=ctx.command.name if ctx.command else "unknown",
            current_channel=ctx.channel.name,
            session_channel=getattr(session_channel, "name", self.session.text_channel_id),
        ))
        return True

    def check_voice_channel(self, voice: VoiceContext) -> VoiceChannelReject | None:
        if voice.vc is None:
            return VoiceChannelReject.BOT_NOT_CONNECTED

        if voice.user_channel is None:
            return VoiceChannelReject.USER_NOT_CONNECTED

        if voice.user_channel != voice.vc.channel:
            return VoiceChannelReject.DIFFERENT_VOICE_CHANNEL

        return None

    async def reject_invalid_voice_channel(self, ctx, voice: VoiceContext) -> bool:
        error = self.check_voice_channel(voice)

        if error is None:
            return False

        match error:
            case VoiceChannelReject.BOT_NOT_CONNECTED:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
                logger.info(msg.LOG_COMMAND_FAILED_BOT_ABSENT.format(
                    user=ctx.author.name, 
                    command=ctx.command.name if ctx.command else "unknown",
                ))

            case VoiceChannelReject.USER_NOT_CONNECTED:
                channel = voice.vc.channel.name if voice.vc is not None else "unknown"
                await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
                logger.info(msg.LOG_COMMAND_FAILED_USER_ABSENT.format(
                    user=ctx.author.name, 
                    command=ctx.command.name if ctx.command else "unknown", 
                    channel=channel,
                ))

            case VoiceChannelReject.DIFFERENT_VOICE_CHANNEL:
                user_vc = voice.user_channel.name if voice.user_channel else "unknown"
                bot_vc = voice.vc.channel.name if voice.vc is not None else "unknown"

                await ctx.send(embed=discord.Embed(description=msg.FAIL_DIFFERENT_CHANNEL))
                logger.info(msg.LOG_COMMAND_FAILED_DIFFERENT_VOICE_CHANNEL.format(
                    user=ctx.author.name, 
                    command=ctx.command.name if ctx.command else "unknown", 
                    user_vc=user_vc, 
                    bot_vc=bot_vc,
                ))
        
        return True   

    def get_voice_context(self, ctx) -> VoiceContext:
        user_voice = ctx.author.voice
        user_channel: discord.VoiceChannel | discord.StageChannel | None = user_voice.channel if user_voice and user_voice.channel else None

        return VoiceContext(
            state=self.session.state,
            vc=self.get_vc(ctx.guild),
            user_channel=user_channel,
        )


    # 3. Embed / yt-dlp helders
    def build_queued_track_embed(self, track: Track, position: int, requester):
        """Card posted when a track is queued behind others; styled like the Now playing card."""
        embed = discord.Embed(
            title=track.title,
            url=track.webpage_url,
            color=discord.Color.blue(),
        )
        embed.add_field(name="Length", value=format_track_length(track.duration), inline=True)
        # Counts the full length of the current track, not the time left in it, so it is an estimate
        embed.add_field(name="Starts in", value=format_wait(self.session.queue.time_until(position)), inline=True)
        # Keep the number plain so the columns line up across cards; "up next" goes in the header
        embed.add_field(name="Position", value=f"#{position}", inline=True)
        bot_user = self.bot.user
        icon_url = bot_user.display_avatar.url if bot_user is not None else None

        embed.set_author(icon_url=icon_url, name="Added to queue · up next" if position == 1 else "Added to queue")
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        embed.set_footer(icon_url=requester.display_avatar.url, text=f"requested by {str(requester).capitalize()}")
        return embed

    def build_now_playing_embed(self, track: Track, requester):
        """Card posted when a requested track starts right away; styled like the Added to queue card."""
        embed = discord.Embed(
            title=track.title,
            url=track.webpage_url,
            color=discord.Color.blue(),
        )
        embed.add_field(name="Length", value=format_track_length(track.duration), inline=True)
        bot_user = self.bot.user
        icon_url = bot_user.display_avatar.url if bot_user is not None else None

        embed.set_author(icon_url=icon_url, name="Now playing")
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        embed.set_footer(icon_url=requester.display_avatar.url, text=f"requested by {str(requester).capitalize()}")
        return embed

    async def search_youtube(self, query: str) -> tuple[Track | None, str | None]:
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

        return Track(
            title=entry.get('title') or "Unknown title",
            webpage_url=webpage_url,
            duration=int(entry.get('duration') or 0),
            thumbnail=thumbnail,
        ), None

    # 4. Queueing
    async def get_queueing_channel(self, ctx) -> discord.VoiceChannel | discord.StageChannel | None:
        """The user's voice channel if they may queue tracks from it; otherwise reply and return None."""
        voice = self.get_voice_context(ctx)

        if voice.user_channel is None:
            logger.info(msg.LOG_PLAY_FAILED_USER_NOT_CONNECTED.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_USER_NOT_CONNECTED))
            return None

        if voice.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            if voice.vc is None:
                logger.warning("Playback state was %s but voice client was missing", voice.state)
                await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_CONNECTED))
                return None

            if voice.user_channel != voice.vc.channel:
                await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_QUEUE_FROM_OTHER_CHANNEL.format(channel=voice.vc.channel.name)))
                logger.info(msg.LOG_PLAY_FAILED_USER_CHANNEL_OTHER.format(user=ctx.author.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
                return None

        return voice.user_channel

    async def enqueue_queries(self, ctx, queries: list[str], user_channel) -> tuple[int, bool]:
        """Search, queue and announce each query in turn; start playback on the first track found.

        Returns how many tracks were added, and whether it stopped early because the voice
        session ended or could not connect (both already told the user).
        """
        added = 0
        end_count = self.session.end_count

        for query in queries:
            track = await self.resolve_track(ctx, query)

            # The session ended (stop, disconnect) while searching: don't queue into a new one
            if self.session.end_count != end_count:
                logger.info(msg.LOG_QUEUEING_STOPPED_SESSION_ENDED.format(user=ctx.author.name, added=added, requested=len(queries)))
                return added, True

            if track is None:
                continue

            if self.session.state in (PlaybackState.DISCONNECTED, PlaybackState.IDLE):
                vc = self.get_vc(ctx.guild)
                if vc is None or vc.channel != user_channel:
                    if not await self.connect_session(ctx, user_channel):
                        return added, True

                self.queue_track(track)
                await ctx.send(embed=self.build_now_playing_embed(track, ctx.author))
                await self.session.start(ctx.channel.id)
            else:
                position = self.queue_track(track)
                await ctx.send(embed=self.build_queued_track_embed(track, position, ctx.author))

            added += 1

        return added, False

    async def resolve_track(self, ctx, query: str) -> Track | None:
        """Search for one query; on failure reply with the query and the reason, and return None."""
        track, reason = await self.search_youtube(query)

        if track is None:
            reason = reason or msg.PLAY_FAIL_VIDEO_NOT_FOUND
        elif track.duration > MAX_TRACK_SECONDS:
            reason = msg.PLAY_FAIL_VIDEO_TOO_LONG.format(minutes=MAX_TRACK_SECONDS // 60)
            logger.info(msg.LOG_PLAY_FAILED_TOO_LONG.format(query=query, user=ctx.author.name))
        else:
            return track

        await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_TRACK.format(
            query=discord.utils.escape_markdown(query),
            reason=reason,
        )))
        return None

    def queue_track(self, track: Track) -> int:
        position = self.session.queue.enqueue(track)
        logger.info(msg.LOG_PLAY_TRACK_QUEUED.format(title=track.title, webpage_url=track.webpage_url))
        return position


    # 5. Listeners
    @commands.Cog.listener()
    async def on_command(self, ctx):
        logger.info(f"{ctx.command.name.capitalize()} command requested: User {ctx.author.name} in {ctx.channel.name}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if self.bot.user is not None and member.id == self.bot.user.id:
            if before.channel is not None and after.channel is None:
                logger.warning("Bot voice state changed to disconnected. Waiting before cleanup.")
                await asyncio.sleep(3)

                if isinstance(member.guild.voice_client, discord.VoiceClient):
                    logger.info("Voice client still exists after disconnect event. Keeping voice session")
                    return

                # Already ended by !stop or a timeout
                if self.session.state == PlaybackState.DISCONNECTED:
                    return

                logger.warning("Bot was fully disconnected from voice. Clearing playback state.")
                await self.session.end(EndReason.DISCONNECTED)

            return

        vc = self.get_vc(member.guild)
        if vc is None or vc.channel is None:
            return

        if before.channel != vc.channel and after.channel != vc.channel:
            return

        self.session.on_members_changed()


    # 6. Commands
    @commands.command(name="join", aliases=['connect'], help=msg.HELP_MESSAGES['join'], usage=msg.HELP_USAGES['join'])
    async def join(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
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
                self.session.on_members_changed()  # restarts the IDLE timeout when idle
                await ctx.send(embed=discord.Embed(description=msg.JOIN_FAIL_SAME_CHANNEL))
                logger.info(msg.LOG_JOIN_FAILED_USER_CHANNEL_SAME.format(user=user.name, channel=voice.vc.channel.name))
                return
            if voice.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
                await ctx.send(embed=discord.Embed(description=msg.JOIN_FAIL_PLAYING_OTHER_CHANNEL))
                logger.info(msg.LOG_JOIN_FAILED_PLAYBACK_OTHER.format(user=user.name, user_vc=voice.user_channel.name, bot_vc=voice.vc.channel.name))
                return
            
            # Bot is idle in another channel: move
            old_channel_name = voice.vc.channel.name


        if not await self.connect_session(ctx, voice.user_channel):
            return

        if old_channel_name is None:
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_CONNECTED.format(channel=voice.user_channel.name)))
            logger.info(msg.LOG_JOIN_CHANNEL_CONNECT.format(user=user.name, channel=voice.user_channel.name))
        else: 
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_MOVED.format(channel=voice.user_channel.name)))
            logger.info(msg.LOG_JOIN_CHANNEL_MOVE.format(user=user.name, old=old_channel_name, new=voice.user_channel.name))


    @commands.command(name="play", aliases=["p", "pl"], help=msg.HELP_MESSAGES['play'], usage=msg.HELP_USAGES['play'])
    async def play(self, ctx, *args):
        if await self.reject_invalid_text_channel(ctx):
            return

        if not args:
            logger.info(msg.LOG_PLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_NO_ARGS))
            return

        user_channel = await self.get_queueing_channel(ctx)
        if user_channel is None:
            return

        await self.enqueue_queries(ctx, [" ".join(args)], user_channel)


    @commands.command(name="multiplay", aliases=["mp", "mplay", "mb"], help=msg.HELP_MESSAGES['multiplay'], usage=msg.HELP_USAGES['multiplay'])
    async def multiplay(self, ctx, *args):
        if await self.reject_invalid_text_channel(ctx):
            return

        if not args:
            logger.info(msg.LOG_MULTIPLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_NO_ARGS))
            return 

        user_channel = await self.get_queueing_channel(ctx)
        if user_channel is None:
            return

        searches = [
            search.strip() 
            for search in " ".join(args).split('|')
            if search.strip()
        ]
        
        if not searches:
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_NO_ARGS))
            return 

        if len(searches) > MULTIPLAY_MAX_TRACKS:
            await ctx.send(embed=discord.Embed(description=msg.MULTIPLAY_MAX_TRACKS.format(number=MULTIPLAY_MAX_TRACKS)))
            searches = searches[:MULTIPLAY_MAX_TRACKS]

        added, stopped = await self.enqueue_queries(ctx, searches, user_channel)

        # Only summarise when a search failed; every success already has its own line,
        # and an early stop was already announced (stop, disconnect or connection error)
        if added < len(searches) and not stopped:
            await ctx.send(embed=discord.Embed(description=msg.MULTIPLAY_SUMMARY.format(added=added, requested=len(searches))))

        logger.info(msg.LOG_MULTIPLAY_EXECUTED.format(added=added, requested=len(searches), user=ctx.author.name))


    @commands.command(name="pause", help=msg.HELP_MESSAGES["pause"], usage=msg.HELP_USAGES["pause"])
    async def pause(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
            return

        voice = self.get_voice_context(ctx)
        user = ctx.author

        if await self.reject_invalid_voice_channel(ctx, voice):
            return
            
        if voice.state == PlaybackState.IDLE:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PLAYING))
            logger.info(msg.LOG_PAUSE_FAILED_NOT_PLAYING.format(user=user.name))
            return 

        if voice.state == PlaybackState.PAUSED:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_ALREADY_PAUSED))
            logger.info(msg.LOG_PAUSE_FAILED_ALREADY_PAUSED.format(user=user.name)) 
            return 
        
        self.session.pause()

        await ctx.send(embed=discord.Embed(description=msg.PAUSED))
        logger.info(msg.LOG_PAUSE_EXECUTED.format(user=user.name))


    @commands.command(name = "resume", aliases=["r"], help=msg.HELP_MESSAGES['resume'], usage=msg.HELP_USAGES['resume'])
    async def resume(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
            return

        voice = self.get_voice_context(ctx)

        if await self.reject_invalid_voice_channel(ctx, voice):
            return

        if voice.state == PlaybackState.PLAYING:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_ALREADY_PLAYING))
            logger.info(msg.LOG_RESUME_FAILED_ALREADY_PLAYING.format(user=ctx.author.name))
            return

        if voice.state != PlaybackState.PAUSED:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PAUSED))
            logger.info(msg.LOG_RESUME_FAILED_NOT_PAUSED.format(user=ctx.author.name))
            return 

        self.session.resume()

        await ctx.send(embed=discord.Embed(description=msg.RESUMED))
        logger.info(msg.LOG_RESUME_EXECUTED.format(user=ctx.author.name))


    @commands.command(name="skip", aliases=["s"], help=msg.HELP_MESSAGES['skip'], usage=msg.HELP_USAGES['skip'])
    async def skip(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
            return

        user = ctx.author
        voice = self.get_voice_context(ctx)

        if await self.reject_invalid_voice_channel(ctx, voice):
            return
        assert voice.vc is not None

        if voice.state not in (PlaybackState.PLAYING, PlaybackState.PAUSED) or self.session.queue.current is None:
            logger.info(msg.LOG_SKIP_FAILED_NO_AUDIO.format(user=user.name, channel=voice.vc.channel.name))
            await ctx.send(embed=discord.Embed(description=msg.SKIP_FAIL_NOTHING_TO_SKIP))
            return

        track = self.session.skip()
        if track is None:
            return

        await ctx.send(embed=discord.Embed(description=msg.SKIP_TRACK.format(title=track.title, webpage_url=track.webpage_url)))
        logger.info(msg.LOG_TRACK_SKIPPED.format(title=track.title, user=user.name))


    @commands.command(name="queue", aliases=["q"], help=msg.HELP_MESSAGES['queue'], usage=msg.HELP_USAGES['queue'])
    async def queue(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
            return

        queue = self.session.queue

        if queue.is_empty:
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_EMPTY))
            logger.info(msg.LOG_QUEUE_EMPTY.format(channel=ctx.channel.name))
            return

        vc = self.get_vc(ctx.guild)
        channel_name = vc.channel.name if vc is not None and vc.channel is not None else "Not connected"

        data = {
            "time_label": "Estimated Total Playtime",
            "time": seconds_to_time_format(queue.total_duration),
            "thumbnail": ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None,
            "fields": [],
        }

        current = queue.current
        if current is not None:
            description = msg.QUEUE_START_PLAYBACK.format(
                title=current.title,
                webpage_url=current.webpage_url
            )
        else:
            description = "Nothing currently playing."

        upcoming = queue.upcoming
        for position, track in enumerate(upcoming, start=1):
            data['fields'].append({
                'label': "",
                'item': f"**{position}.** {track.title}",
            })

        pagination_view = PaginationView(
            data=data,
            title=msg.QUEUE_STATUS.format(channel_name=channel_name),
            description=description,
            timeout=None
        )

        await pagination_view.send(ctx)
        
        number_of_tracks = len(upcoming) + (1 if current is not None else 0)

        logger.info(
            msg.LOG_QUEUE_DISPLAYED.format(
                channel=ctx.channel.name, 
                number_of_tracks=number_of_tracks
            )
        )


    @commands.command(name="playing", aliases=["np"], help=msg.HELP_MESSAGES['playing'], usage=msg.HELP_USAGES['playing'])
    async def playing(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
            return

        track = self.session.queue.current

        if track is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PLAYING))
            return

        embed = discord.Embed(description=msg.PLAYING.format(title=track.title, webpage_url=track.webpage_url))
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        await ctx.send(embed=embed)

        return
        

    @commands.command(name="remove", aliases=["rm"], help=msg.HELP_MESSAGES['remove'], usage=msg.HELP_USAGES['remove'])
    async def remove(self, ctx, *args):
        if await self.reject_invalid_text_channel(ctx):
            return        
        
        voice = self.get_voice_context(ctx)

        if await self.reject_invalid_voice_channel(ctx, voice):
            return

        queue = self.session.queue

        if not queue.upcoming:
            logger.info(msg.LOG_REMOVE_FAILED_NO_QUEUE.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_QUEUE_EMPTY))
            return

        if args:
            try:
                position = int(args[0])
            except ValueError:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_INDEX))
                return
        else:
            position = len(queue.upcoming)

        track = queue.remove(position)

        if track is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_INDEX))
            return

        embed = discord.Embed(description=msg.TRACK_REMOVED.format(title=track.title, index=position))

        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        await ctx.send(embed=embed)

        logger.info(
            msg.LOG_REMOVE_LAST_EXECUTED.format(index=position, user=ctx.author.name)
            if not args
            else msg.LOG_REMOVE_EXECUTED.format(index=position, user=ctx.author.name)
        )


    @commands.command(name="clear", aliases=["c", "bin"], help=msg.HELP_MESSAGES['clear'], usage=msg.HELP_USAGES['clear'])
    async def clear(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
            return

        voice = self.get_voice_context(ctx)

        if await self.reject_invalid_voice_channel(ctx, voice):
            return

        if self.session.queue.is_empty:
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_EMPTY))
            logger.info(msg.LOG_QUEUE_EMPTY.format(channel=ctx.channel.name))
            return

        self.session.clear()

        await ctx.send(embed=discord.Embed(description=msg.QUEUE_CLEARED))
        logger.info(msg.LOG_CLEAR_EXECUTED.format(user=ctx.author.name))


    @commands.command(name="stop", aliases=["disconnect"], help=msg.HELP_MESSAGES['stop'], usage=msg.HELP_USAGES['stop'])
    async def stop(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
            return

        voice = self.get_voice_context(ctx)

        if await self.reject_invalid_voice_channel(ctx, voice):
            return
        assert voice.vc is not None

        channel_name = voice.vc.channel.name
        await self.session.end(EndReason.STOPPED)

        logger.info(msg.LOG_STOP_EXECUTED.format(channel=channel_name, user=ctx.author.name))


    @commands.command(name="status", aliases=["stat"], help=msg.HELP_MESSAGES['status'], usage=msg.HELP_USAGES['status'])
    async def status(self, ctx):
        if await self.reject_invalid_text_channel(ctx):
            return

        queue = self.session.queue
        tracks = [track.title for track in queue.upcoming]

        vc = self.get_vc(ctx.guild)

        voice = vc.channel.name if vc is not None and vc.is_connected() else None
        text_channel = self.bot.get_channel(self.session.text_channel_id or 0)
        text = getattr(text_channel, "name", None)
        is_playing = self.session.state == PlaybackState.PLAYING
        is_paused = self.session.state == PlaybackState.PAUSED

        current = queue.current
        current_title = current.title if current is not None else None

        status_description = (    
            f"Playing: {is_playing}\n"
            f"Paused: {is_paused}\n"
            f"Current Track: {current_title}\n"
            f"Queue: {', '.join(tracks)}\n"  # Join the song URLs with a comma and a space
            f"Queue Duration: {queue.total_duration}\n"
            f"Voice Channel: {voice}\n"
            f"Text Channel: {text}"
        )
        
        embed = discord.Embed(
            title=":gear: Bot Status :gear:",
            description=status_description,
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)


    @commands.command(name="tone")
    async def tone(self, ctx):
        """Temporary: play a 10 s test beep without YouTube."""
        channel = ctx.author.voice.channel
        vc = await self.ensure_voice_client(channel)
        vc.play(discord.FFmpegPCMAudio("sine=frequency=440:duration=10", before_options="-f lavfi"))
        await ctx.send("Playing test tone")

