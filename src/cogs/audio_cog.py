import discord
import asyncio
from dataclasses import dataclass
from discord.ext import commands

from src.bot.admission import CommandRequest, Needs, Reject, check
from src.bot.playback import AsyncioTimer, DiscordSessionNotifier, DiscordVoiceConnection
from src.bot.track_resolver import LookupFailure, TrackResolver
from src.audio.track import Track
from src.audio.track_queue import Placement
from src.audio.voice_session import EndReason, PlaybackState, VoiceSession
from src.utils.logging_config import *
import src.utils.message as msg
from src.utils.time_convertion import *
from src.utils.partionation import LinePaginationView
from src.utils.queue_text import format_queue_line

logger = logging.getLogger("audio")

MAX_TRACK_SECONDS = 1800
MULTIPLAY_MAX_TRACKS = 8
QUEUE_TRACKS_PER_PAGE = 10

# Why a search can't be queued, as the reason in "Could not add <search>: <reason>"
LOOKUP_REASONS = {
    LookupFailure.NOT_FOUND: msg.PLAY_FAIL_VIDEO_NOT_FOUND,
    LookupFailure.UNAVAILABLE: msg.PLAY_FAIL_VIDEO_UNAVAILABLE,
    LookupFailure.AGE_RESTRICTED: msg.PLAY_FAIL_VIDEO_AGE_RESTRICTED,
    LookupFailure.NO_JS_RUNTIME: msg.PLAY_FAIL_YTDLP_RUNTIME,
    LookupFailure.YTDLP_ERROR: msg.PLAY_FAIL_YTDLP_ERROR,
    LookupFailure.TOO_LONG: msg.PLAY_FAIL_VIDEO_TOO_LONG,
}


# Replies for rejected commands; WRONG_TEXT_CHANNEL has none on purpose (replies in other channels clutter them)
REJECT_REPLIES = {
    Reject.USER_NOT_IN_VOICE: msg.FAIL_USER_NOT_CONNECTED,
    Reject.BOT_NOT_IN_VOICE: msg.FAIL_BOT_NOT_CONNECTED,
    Reject.BOT_IN_OTHER_CHANNEL: msg.FAIL_DIFFERENT_CHANNEL,
    Reject.BOT_BUSY_ELSEWHERE: msg.FAIL_BOT_BUSY_ELSEWHERE,
}


@dataclass(frozen=True)
class Admitted:
    """A command that passed admission, with what its Needs level guarantees."""

    _vc: discord.VoiceClient | None
    _user_channel: discord.VoiceChannel | discord.StageChannel | None

    @property
    def vc(self) -> discord.VoiceClient:
        """The bot's voice client; guaranteed for Needs.SAME_VOICE."""
        if self._vc is None:
            raise RuntimeError("No voice client: only Needs.SAME_VOICE guarantees one")
        return self._vc

    @property
    def user_channel(self) -> discord.VoiceChannel | discord.StageChannel:
        """The user's voice channel; guaranteed for Needs.SAME_VOICE and Needs.CAN_CONNECT."""
        if self._user_channel is None:
            raise RuntimeError("No user voice channel: Needs.SESSION_CHANNEL does not check voice")
        return self._user_channel


class AudioCog(commands.Cog):

    # 1. Setup & configuration
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        
        self.session = VoiceSession(DiscordSessionNotifier(bot), AsyncioTimer())
        self.resolver = TrackResolver(max_seconds=MAX_TRACK_SECONDS)
        # Joining voice takes a moment, and two commands joining at once would share a half-connected client
        self._join_lock = asyncio.Lock()
        self.logger = logger

        self.logger.info("AudioCog initialized successfully.")

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    # bot.close() removes the cogs first, so this still runs while connected to Discord
    async def cog_unload(self) -> None:
        if self.session.state != PlaybackState.DISCONNECTED:
            await self.session.end(EndReason.SHUTDOWN)

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

    async def admit(self, ctx, needs: Needs) -> Admitted | None:
        """Check whether the command may run here; if not, reply (except in the wrong text channel), log, and return None."""
        user_voice = ctx.author.voice
        user_channel = user_voice.channel if user_voice and user_voice.channel else None
        vc = self.get_vc(ctx.guild)
        bot_channel = vc.channel if vc is not None else None

        reject = check(CommandRequest(
            needs=needs,
            author_id=ctx.author.id,
            text_channel_id=ctx.channel.id,
            user_voice_channel_id=user_channel.id if user_channel is not None else None,
            bot_voice_channel_id=bot_channel.id if bot_channel is not None else None,
            session_state=self.session.state,
            session_text_channel_id=self.session.text_channel_id,
        ))

        if reject is None:
            return Admitted(vc, user_channel)

        logger.info(msg.LOG_COMMAND_REJECTED.format(
            user=ctx.author.name,
            command=ctx.command.name if ctx.command else "unknown",
            text_channel=ctx.channel.name,
            reason=reject,
            user_vc=user_channel.name if user_channel is not None else None,
            bot_vc=bot_channel.name if bot_channel is not None else None,
        ))

        if reject in REJECT_REPLIES:
            reply = REJECT_REPLIES[reject].format(channel=bot_channel.name if bot_channel is not None else "another channel")
            await ctx.send(embed=discord.Embed(description=reply))
        return None


    # 3. Embed / yt-dlp helders
    def build_queued_track_embed(self, track: Track, placement: Placement, requester):
        """Card posted when a track is queued behind others; styled like the Now playing card."""
        embed = discord.Embed(
            title=track.title,
            url=track.webpage_url,
            color=discord.Color.blue(),
        )
        embed.add_field(name="Length", value=format_track_length(track.duration), inline=True)
        # Counts the full length of the current track, not the time left in it, so it is an estimate
        embed.add_field(name="Starts in", value=format_wait(self.session.queue.time_until(placement.position)), inline=True)
        # The only "#" on the card, so nobody mistakes the place in line for the number !remove needs
        embed.add_field(name=msg.CARD_NUMBER, value=f"#{placement.number}", inline=True)
        bot_user = self.bot.user
        icon_url = bot_user.display_avatar.url if bot_user is not None else None

        embed.set_author(icon_url=icon_url, name=self.queued_card_header(placement.position))
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        embed.set_footer(icon_url=requester.display_avatar.url, text=f"requested by {str(requester).capitalize()}")
        return embed

    @staticmethod
    def queued_card_header(position: int) -> str:
        """Header of the Added to queue card; counts waiting tracks ahead, not the current one."""
        ahead = position - 1
        if ahead == 0:
            return msg.CARD_ADDED_UP_NEXT
        return msg.CARD_ADDED_ONE_AHEAD if ahead == 1 else msg.CARD_ADDED_MANY_AHEAD.format(ahead=ahead)

    def build_now_playing_embed(self, track: Track, number: int, requester):
        """Card posted when a requested track starts right away; styled like the Added to queue card."""
        embed = discord.Embed(
            title=track.title,
            url=track.webpage_url,
            color=discord.Color.blue(),
        )
        embed.add_field(name="Length", value=format_track_length(track.duration), inline=True)
        embed.add_field(name=msg.CARD_NUMBER, value=f"#{number}", inline=True)
        bot_user = self.bot.user
        icon_url = bot_user.display_avatar.url if bot_user is not None else None

        embed.set_author(icon_url=icon_url, name="Now playing")
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        embed.set_footer(icon_url=requester.display_avatar.url, text=f"requested by {str(requester).capitalize()}")
        return embed

    # 4. Queueing
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

            if not await self.join_if_needed(ctx, user_channel):
                return added, True

            # Nothing waits between reading the state and start() marking the session STARTING,
            # so no other command can slip in here
            placement = self.queue_track(track)
            if self.session.state == PlaybackState.IDLE:
                await self.session.start(ctx.channel.id)

            await self.announce_track(ctx, track, placement.number)
            added += 1

        return added, False

    async def join_if_needed(self, ctx, user_channel) -> bool:
        """Join the user's voice channel unless the session is already busy; False if that failed.

        One command joins at a time. A command that had to wait finds the bot connected, and
        usually already starting a track, so it only has to queue its own.
        """
        async with self._join_lock:
            if self.session.state not in (PlaybackState.DISCONNECTED, PlaybackState.IDLE):
                return True

            vc = self.get_vc(ctx.guild)
            if vc is not None and vc.channel == user_channel:
                return True

            return await self.connect_session(ctx, user_channel)

    async def announce_track(self, ctx, track: Track, number: int) -> None:
        """Post the card that fits where the track is now: playing, or waiting in the queue."""
        queue = self.session.queue

        if queue.current is track:
            await ctx.send(embed=self.build_now_playing_embed(track, number, ctx.author))
        elif (position := queue.position_of(number)) is not None:
            await ctx.send(embed=self.build_queued_track_embed(track, Placement(number, position), ctx.author))
        # Otherwise it could not start, and the session already posted why

    async def resolve_track(self, ctx, query: str) -> Track | None:
        """Search for one query; on failure reply with the query and the reason, and return None."""
        result = await self.resolver.resolve(query)

        if isinstance(result, Track):
            return result

        reason = LOOKUP_REASONS[result].format(minutes=self.resolver.max_seconds // 60)
        await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_TRACK.format(
            query=discord.utils.escape_markdown(query),
            reason=reason,
        )))
        return None

    def queue_track(self, track: Track) -> Placement:
        placement = self.session.queue.enqueue(track)
        logger.info(msg.LOG_PLAY_TRACK_QUEUED.format(title=track.title, webpage_url=track.webpage_url))
        return placement


    # 5. Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        # A crash or hard kill can leave the bot shown in a voice channel without a connection
        # to it; tell Discord it left. on_ready also runs after reconnects, where the voice
        # client still exists, so a live session is never touched.
        for guild in self.bot.guilds:
            # guild.me can be empty at startup, even though its type says it never is
            voice = guild.me.voice if guild.me is not None else None
            if voice is None or voice.channel is None or guild.voice_client is not None:
                continue

            logger.info(msg.LOG_LEFT_LEFTOVER_VOICE.format(channel=voice.channel.name, guild=guild.name))
            await guild.change_voice_state(channel=None)

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
        if (admitted := await self.admit(ctx, Needs.CAN_CONNECT)) is None:
            return

        user = ctx.author
        user_channel = admitted.user_channel
        vc = self.get_vc(ctx.guild)
        old_channel_name: str | None = None

        if vc is not None:
            if vc.channel == user_channel:
                self.session.on_members_changed()  # restarts the IDLE timeout when idle
                await ctx.send(embed=discord.Embed(description=msg.JOIN_FAIL_SAME_CHANNEL))
                logger.info(msg.LOG_JOIN_FAILED_USER_CHANNEL_SAME.format(user=user.name, channel=vc.channel.name))
                return

            # Bot is idle in another channel (admission rejects it when busy there): move
            old_channel_name = vc.channel.name


        if not await self.connect_session(ctx, user_channel):
            return

        if old_channel_name is None:
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_CONNECTED.format(channel=user_channel.name)))
            logger.info(msg.LOG_JOIN_CHANNEL_CONNECT.format(user=user.name, channel=user_channel.name))
        else: 
            await ctx.send(embed=discord.Embed(description=msg.BOT_CHANNEL_MOVED.format(channel=user_channel.name)))
            logger.info(msg.LOG_JOIN_CHANNEL_MOVE.format(user=user.name, old=old_channel_name, new=user_channel.name))


    @commands.command(name="play", aliases=["p", "pl"], help=msg.HELP_MESSAGES['play'], usage=msg.HELP_USAGES['play'])
    async def play(self, ctx, *args):
        if (admitted := await self.admit(ctx, Needs.CAN_CONNECT)) is None:
            return

        if not args:
            logger.info(msg.LOG_PLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_NO_ARGS))
            return

        await self.enqueue_queries(ctx, [" ".join(args)], admitted.user_channel)


    @commands.command(name="multiplay", aliases=["mp", "mplay", "mb"], help=msg.HELP_MESSAGES['multiplay'], usage=msg.HELP_USAGES['multiplay'])
    async def multiplay(self, ctx, *args):
        if (admitted := await self.admit(ctx, Needs.CAN_CONNECT)) is None:
            return

        if not args:
            logger.info(msg.LOG_MULTIPLAY_FAILED_NO_ARGS.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.PLAY_FAIL_NO_ARGS))
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

        added, stopped = await self.enqueue_queries(ctx, searches, admitted.user_channel)

        # Only summarise when a search failed; every success already has its own line,
        # and an early stop was already announced (stop, disconnect or connection error)
        if added < len(searches) and not stopped:
            await ctx.send(embed=discord.Embed(description=msg.MULTIPLAY_SUMMARY.format(added=added, requested=len(searches))))

        logger.info(msg.LOG_MULTIPLAY_EXECUTED.format(added=added, requested=len(searches), user=ctx.author.name))


    @commands.command(name="pause", help=msg.HELP_MESSAGES["pause"], usage=msg.HELP_USAGES["pause"])
    async def pause(self, ctx):
        if await self.admit(ctx, Needs.SAME_VOICE) is None:
            return

        user = ctx.author
        state = self.session.state

        if state in (PlaybackState.IDLE, PlaybackState.STARTING):
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PLAYING))
            logger.info(msg.LOG_PAUSE_FAILED_NOT_PLAYING.format(user=user.name))
            return 

        if state == PlaybackState.PAUSED:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_ALREADY_PAUSED))
            logger.info(msg.LOG_PAUSE_FAILED_ALREADY_PAUSED.format(user=user.name)) 
            return 
        
        self.session.pause()

        await ctx.send(embed=discord.Embed(description=msg.PAUSED))
        logger.info(msg.LOG_PAUSE_EXECUTED.format(user=user.name))


    @commands.command(name = "resume", aliases=["r"], help=msg.HELP_MESSAGES['resume'], usage=msg.HELP_USAGES['resume'])
    async def resume(self, ctx):
        if await self.admit(ctx, Needs.SAME_VOICE) is None:
            return

        state = self.session.state

        if state == PlaybackState.PLAYING:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_ALREADY_PLAYING))
            logger.info(msg.LOG_RESUME_FAILED_ALREADY_PLAYING.format(user=ctx.author.name))
            return

        if state != PlaybackState.PAUSED:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_BOT_NOT_PAUSED))
            logger.info(msg.LOG_RESUME_FAILED_NOT_PAUSED.format(user=ctx.author.name))
            return 

        self.session.resume()

        await ctx.send(embed=discord.Embed(description=msg.RESUMED))
        logger.info(msg.LOG_RESUME_EXECUTED.format(user=ctx.author.name))


    @commands.command(name="skip", aliases=["s"], help=msg.HELP_MESSAGES['skip'], usage=msg.HELP_USAGES['skip'])
    async def skip(self, ctx):
        if (admitted := await self.admit(ctx, Needs.SAME_VOICE)) is None:
            return

        await self.skip_current(ctx, admitted.vc)

    async def skip_current(self, ctx, vc: discord.VoiceClient) -> None:
        """Skip the current track and tell the user; used by !skip and by !remove on the current track."""
        user = ctx.author

        if self.session.state not in (PlaybackState.PLAYING, PlaybackState.PAUSED) or self.session.queue.current is None:
            logger.info(msg.LOG_SKIP_FAILED_NO_AUDIO.format(user=user.name, channel=vc.channel.name))
            await ctx.send(embed=discord.Embed(description=msg.SKIP_FAIL_NOTHING_TO_SKIP))
            return

        track = self.session.skip()
        if track is None:
            return

        await ctx.send(embed=discord.Embed(description=msg.SKIP_TRACK.format(title=track.title, webpage_url=track.webpage_url)))
        logger.info(msg.LOG_TRACK_SKIPPED.format(title=track.title, user=user.name))


    @commands.command(name="queue", aliases=["q"], help=msg.HELP_MESSAGES['queue'], usage=msg.HELP_USAGES['queue'])
    async def queue(self, ctx):
        if await self.admit(ctx, Needs.SESSION_CHANNEL) is None:
            return

        queue = self.session.queue

        if queue.is_empty:
            await ctx.send(embed=discord.Embed(description=msg.QUEUE_EMPTY))
            logger.info(msg.LOG_QUEUE_EMPTY.format(channel=ctx.channel.name))
            return

        vc = self.get_vc(ctx.guild)
        channel_name = vc.channel.name if vc is not None and vc.channel is not None else "Not connected"

        current = queue.current
        if current is not None:
            description = msg.QUEUE_CURRENT.format(
                number=queue.current_number,
                title=discord.utils.escape_markdown(current.title),
                webpage_url=current.webpage_url,
                length=format_track_length(current.duration),
            )
        else:
            description = msg.QUEUE_NOTHING_PLAYING

        upcoming = queue.numbered_upcoming
        if upcoming:
            description += msg.QUEUE_UP_NEXT

        number_of_tracks = len(upcoming) + (1 if current is not None else 0)

        pagination_view = LinePaginationView(
            data={
                "thumbnail": current.thumbnail if current is not None else None,
                "fields": [format_queue_line(queued) for queued in upcoming],
                "summary": msg.QUEUE_SUMMARY.format(
                    tracks=number_of_tracks,
                    total=format_wait(queue.total_duration),
                ),
            },
            title=msg.QUEUE_STATUS.format(channel_name=channel_name),
            description=description,
            timeout=None,
            sep=QUEUE_TRACKS_PER_PAGE,
        )

        await pagination_view.send(ctx)

        logger.info(
            msg.LOG_QUEUE_DISPLAYED.format(
                channel=ctx.channel.name, 
                number_of_tracks=number_of_tracks
            )
        )


    @commands.command(name="playing", aliases=["np"], help=msg.HELP_MESSAGES['playing'], usage=msg.HELP_USAGES['playing'])
    async def playing(self, ctx):
        if await self.admit(ctx, Needs.SESSION_CHANNEL) is None:
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
        if (admitted := await self.admit(ctx, Needs.SAME_VOICE)) is None:
            return

        queue = self.session.queue
        number = None

        if args:
            try:
                number = int(args[0])
            except ValueError:
                await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_NUMBER))
                return

            # Checked before the empty queue, because the current track may be the only one left
            if number == queue.current_number:
                await self.skip_current(ctx, admitted.vc)
                return

        if not queue.upcoming:
            logger.info(msg.LOG_REMOVE_FAILED_NO_QUEUE.format(user=ctx.author.name))
            await ctx.send(embed=discord.Embed(description=msg.FAIL_QUEUE_EMPTY))
            return

        if number is None:
            number = queue.numbered_upcoming[-1].number

        track = queue.remove_number(number)

        if track is None:
            await ctx.send(embed=discord.Embed(description=msg.FAIL_INVALID_NUMBER))
            return

        embed = discord.Embed(description=msg.TRACK_REMOVED.format(title=track.title, number=number))

        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        await ctx.send(embed=embed)

        logger.info(
            msg.LOG_REMOVE_LAST_EXECUTED.format(number=number, user=ctx.author.name)
            if not args
            else msg.LOG_REMOVE_EXECUTED.format(number=number, user=ctx.author.name)
        )


    @commands.command(name="clear", aliases=["c", "bin"], help=msg.HELP_MESSAGES['clear'], usage=msg.HELP_USAGES['clear'])
    async def clear(self, ctx):
        if await self.admit(ctx, Needs.SAME_VOICE) is None:
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
        if (admitted := await self.admit(ctx, Needs.SAME_VOICE)) is None:
            return

        channel_name = admitted.vc.channel.name
        await self.session.end(EndReason.STOPPED)

        logger.info(msg.LOG_STOP_EXECUTED.format(channel=channel_name, user=ctx.author.name))


    @commands.command(name="status", aliases=["stat"], help=msg.HELP_MESSAGES['status'], usage=msg.HELP_USAGES['status'])
    async def status(self, ctx):
        if await self.admit(ctx, Needs.SESSION_CHANNEL) is None:
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
