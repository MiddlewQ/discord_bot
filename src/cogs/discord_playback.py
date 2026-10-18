import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import discord
from discord.ext import commands
from yt_dlp import YoutubeDL

from src.audio.track import Track
from src.audio.voice_session import EndReason
from src.utils.logging_config import logging
import src.utils.message as msg

logger = logging.getLogger("audio")

FFMPEG_OPTIONS = "-vn"
FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

END_MESSAGES = {
    EndReason.NO_HUMANS: msg.TIMEOUT_NO_HUMANS,
    EndReason.IDLE: msg.TIMEOUT_IDLE,
    EndReason.PAUSED: msg.TIMEOUT_PAUSED,
    EndReason.STOPPED: msg.STOP_BY_USER,
    EndReason.DISCONNECTED: msg.DISCONNECTED_FROM_VOICE,
}


class DiscordVoiceConnection:
    """VoiceConnection backed by a discord VoiceClient, streaming through yt-dlp and FFmpeg."""

    def __init__(self, vc: discord.VoiceClient, ytdl: YoutubeDL):
        self._vc = vc
        self._ytdl = ytdl

    def is_playing(self) -> bool:
        return self._vc.is_playing()

    def is_paused(self) -> bool:
        return self._vc.is_paused()

    def human_count(self) -> int:
        return sum(1 for member in self._vc.channel.members if not member.bot)

    async def play(self, track: Track, on_end: Callable[[], Coroutine[Any, Any, None]]) -> None:
        loop = asyncio.get_running_loop()

        # The stream URL expires, so it is fetched when the track starts, not when it is queued
        data = await loop.run_in_executor(
            None,
            lambda: self._ytdl.extract_info(track.webpage_url, download=False),
        )

        if not isinstance(data, dict):
            raise ValueError("yt-dlp returned invalid data")

        stream_url = data.get("url")
        if not isinstance(stream_url, str) or not stream_url:
            raise ValueError(f"No valid stream URL found for {track.title}")

        source = discord.FFmpegPCMAudio(
            source=stream_url,
            executable="ffmpeg",
            options=FFMPEG_OPTIONS,
            before_options=FFMPEG_BEFORE_OPTIONS,
        )

        # discord calls after= from its audio thread, so hand on_end back to the event loop
        def after(error: Exception | None) -> None:
            if error is not None:
                logger.warning(f"Playback ended with error: {error}")
            asyncio.run_coroutine_threadsafe(on_end(), loop)

        self._vc.play(source, after=after)

    def pause(self) -> None:
        self._vc.pause()

    def resume(self) -> None:
        self._vc.resume()

    def stop(self) -> None:
        self._vc.stop()

    async def disconnect(self) -> None:
        await self._vc.disconnect()


class AsyncioTimer:
    """Timer that runs its callback in an asyncio task."""

    def __init__(self):
        self._task: asyncio.Task | None = None

    def start(self, seconds: int, callback: Callable[[], Awaitable[None]]) -> None:
        self.cancel()
        self._task = asyncio.create_task(self._run(seconds, callback))

    def cancel(self) -> None:
        task, self._task = self._task, None

        # The callback may end the session, which cancels the timer from inside its own task
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    async def _run(self, seconds: int, callback: Callable[[], Awaitable[None]]) -> None:
        await asyncio.sleep(seconds)
        await callback()


class DiscordSessionListener:
    """SessionListener that posts session messages to the session text channel."""

    def __init__(self, bot: commands.Bot):
        self._bot = bot

    async def track_failed(self, track: Track, text_channel_id: int | None) -> None:
        await self._send(text_channel_id, msg.FAIL_PLAYBACK)

    async def session_ended(self, reason: EndReason, text_channel_id: int | None) -> None:
        await self._send(text_channel_id, END_MESSAGES[reason])

    async def _send(self, text_channel_id: int | None, message: str) -> None:
        if text_channel_id is None:
            return

        channel = self._bot.get_channel(text_channel_id)

        if not isinstance(channel, discord.abc.Messageable):
            logger.warning(f"Session text channel {text_channel_id} not found. Message not sent: {message}")
            return

        await channel.send(embed=discord.Embed(description=message))
