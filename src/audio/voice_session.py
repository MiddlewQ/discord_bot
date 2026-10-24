import logging
from collections.abc import Awaitable, Callable, Coroutine
from enum import StrEnum, auto
from functools import partial
from typing import Any, Protocol

from src.audio.track import Track
from src.audio.track_queue import TrackQueue

logger = logging.getLogger("audio")


class PlaybackState(StrEnum):
    DISCONNECTED = auto()
    IDLE = auto()
    PLAYING = auto()
    PAUSED = auto()


class EndReason(StrEnum):
    NO_HUMANS = auto()
    IDLE = auto()
    PAUSED = auto()
    STOPPED = auto()
    DISCONNECTED = auto()


TIMEOUT_SECONDS = {
    EndReason.NO_HUMANS: 120,
    EndReason.IDLE: 600,
    EndReason.PAUSED: 1800,
}


class VoiceConnection(Protocol):
    """What the session needs from a connected voice client."""

    def is_playing(self) -> bool: ...
    def is_paused(self) -> bool: ...
    def human_count(self) -> int: ...

    async def play(self, track: Track, on_end: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """Start streaming the track; raise if it can't start. Await on_end when it stops."""
        ...

    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...
    async def disconnect(self) -> None: ...


class Timer(Protocol):
    """Runs one callback after a delay. start() replaces any running timeout."""

    def start(self, seconds: int, callback: Callable[[], Awaitable[None]]) -> None: ...
    def cancel(self) -> None: ...


class SessionNotifier(Protocol):
    """How the session tells users what happened, in the session text channel."""

    async def track_failed(self, track: Track, text_channel_id: int | None) -> None: ...
    async def session_ended(self, reason: EndReason, text_channel_id: int | None) -> None: ...


class VoiceSession:
    """One voice connection with its track queue, text channel lock and timeouts."""

    def __init__(self, notifier: SessionNotifier, timer: Timer):
        self.queue = TrackQueue()
        # Where session messages go; commands are only accepted from it while playing or paused
        self.text_channel_id: int | None = None
        self._connection: VoiceConnection | None = None
        self._notifier = notifier
        self._timer = timer

    @property
    def state(self) -> PlaybackState:
        if self._connection is None:
            return PlaybackState.DISCONNECTED
        if self._connection.is_paused():
            return PlaybackState.PAUSED
        if self._connection.is_playing():
            return PlaybackState.PLAYING
        return PlaybackState.IDLE

    def attach(self, connection: VoiceConnection, text_channel_id: int) -> None:
        """Use a connection the cog has just opened or moved."""
        self._connection = connection
        self.text_channel_id = text_channel_id

        if self.state == PlaybackState.IDLE:
            self._start_timeout(EndReason.IDLE)

    def accepts_commands_from(self, channel_id: int) -> bool:
        if self.state not in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            return True
        return self.text_channel_id is None or channel_id == self.text_channel_id

    async def start(self, text_channel_id: int) -> None:
        """Play the next queued track, unless something is already playing or paused."""
        if self.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            return

        self.text_channel_id = text_channel_id
        await self._play_next()

    async def on_track_ended(self) -> None:
        await self._play_next()

    def pause(self) -> None:
        if self._connection is None:
            return
        self._connection.pause()
        self._start_timeout(EndReason.PAUSED)

    def resume(self) -> None:
        if self._connection is None:
            return
        self._connection.resume()
        self._timer.cancel()

    def skip(self) -> Track | None:
        """Stop the current track and return it; the next one starts from on_track_ended."""
        if self._connection is None:
            return None
        track = self.queue.current
        self._connection.stop()
        return track

    def clear(self) -> None:
        self.queue.clear()

        if self._connection is None:
            return

        if self._connection.is_playing() or self._connection.is_paused():
            self._connection.stop()  # on_track_ended then finds nothing and starts the IDLE timeout
        else:
            self._start_timeout(EndReason.IDLE)

    def on_members_changed(self) -> None:
        if self._connection is None:
            return

        if self._connection.human_count() == 0:
            self._start_timeout(EndReason.NO_HUMANS)
            return

        match self.state:
            case PlaybackState.PLAYING:
                self._timer.cancel()
            case PlaybackState.PAUSED:
                self._start_timeout(EndReason.PAUSED)
            case PlaybackState.IDLE:
                self._start_timeout(EndReason.IDLE)

    async def end(self, reason: EndReason) -> None:
        """The only way a session ends: cancel the timeout, clear the queue, disconnect, notify."""
        connection = self._connection
        text_channel_id = self.text_channel_id

        # Mark the session as gone before disconnecting, so on_track_ended has nothing to play.
        self._timer.cancel()
        self.queue.clear()
        self._connection = None
        self.text_channel_id = None

        if connection is not None:
            await connection.disconnect()

        logger.info("Voice session ended: reason=%s.", reason)
        await self._notifier.session_ended(reason, text_channel_id)

    async def _play_next(self) -> None:
        while (track := self.queue.advance()) is not None:
            if self._connection is None:
                self.queue.clear()
                return

            try:
                await self._connection.play(track, on_end=self.on_track_ended)
            except Exception:
                logger.exception("Failed to play track '%s'.", track.title)
                await self._notifier.track_failed(track, self.text_channel_id)
                continue

            self._timer.cancel()
            logger.info("Now playing '%s'.", track.title)
            return

        if self._connection is not None:
            self._start_timeout(EndReason.IDLE)

    def _start_timeout(self, reason: EndReason) -> None:
        seconds = TIMEOUT_SECONDS[reason]
        logger.info("Starting timeout: reason=%s, seconds=%s.", reason, seconds)
        self._timer.start(seconds, partial(self.end, reason))
