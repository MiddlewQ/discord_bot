import asyncio
import io
import subprocess
import sys
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import discord
from discord.ext import commands

from src.audio.track import Track
from src.audio.voice_session import EndReason
from src.utils.logging_config import logging
import src.utils.message as msg

logger = logging.getLogger("audio")

FFMPEG_OPTIONS = "-vn"
YTDLP_AUDIO_FORMAT = "bestaudio[ext=m4a]/bestaudio/best"
STREAM_START_TIMEOUT_SECONDS = 30

END_MESSAGES = {
    EndReason.NO_HUMANS: msg.TIMEOUT_NO_HUMANS,
    EndReason.IDLE: msg.TIMEOUT_IDLE,
    EndReason.PAUSED: msg.TIMEOUT_PAUSED,
    EndReason.STOPPED: msg.STOP_BY_USER,
    EndReason.DISCONNECTED: msg.DISCONNECTED_FROM_VOICE,
}


async def start_stream_process(args: list[str], timeout: float) -> subprocess.Popen:
    """Start a process that writes audio to stdout, and wait until its first bytes arrive.

    Raises RuntimeError if it exits without output (e.g. YouTube refused the stream)
    or produces nothing within the timeout. The waiting does not consume any output.
    """
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = process.stdout
    assert isinstance(stdout, io.BufferedReader) and process.stderr is not None  # what Popen gives for PIPE

    loop = asyncio.get_running_loop()
    try:
        first_bytes = await asyncio.wait_for(loop.run_in_executor(None, stdout.peek), timeout)
    except asyncio.TimeoutError:
        stop_stream_process(process)
        raise RuntimeError(f"No audio after {timeout} seconds")

    if not first_bytes:
        process.wait()
        error = process.stderr.read().decode(errors="replace").strip().splitlines()
        raise RuntimeError(error[-1] if error else f"Stream process exited with code {process.returncode}")

    return process


def stop_stream_process(process: subprocess.Popen) -> None:
    process.kill()
    process.wait()
    if process.stdout is not None:
        process.stdout.close()
    if process.stderr is not None:
        process.stderr.close()


class DiscordVoiceConnection:
    """VoiceConnection backed by a discord VoiceClient, streaming through yt-dlp and FFmpeg."""

    def __init__(self, vc: discord.VoiceClient):
        self._vc = vc

    def is_playing(self) -> bool:
        return self._vc.is_playing()

    def is_paused(self) -> bool:
        return self._vc.is_paused()

    def human_count(self) -> int:
        return sum(1 for member in self._vc.channel.members if not member.bot)

    async def play(self, track: Track, on_end: Callable[[], Coroutine[Any, Any, None]]) -> None:
        loop = asyncio.get_running_loop()

        # yt-dlp downloads the audio itself and pipes it to FFmpeg. YouTube can hand out stream
        # URLs that are only valid after a few seconds (yt-dlp's "available_at"); yt-dlp waits
        # for that, while FFmpeg would request right away and get 403 Forbidden.
        downloader = await start_stream_process(
            [sys.executable, "-m", "yt_dlp", "--quiet", "--no-warnings", "--no-playlist",
             "--format", YTDLP_AUDIO_FORMAT, "--output", "-", track.webpage_url],
            timeout=STREAM_START_TIMEOUT_SECONDS,
        )
        stdout = downloader.stdout
        assert isinstance(stdout, io.BufferedReader)

        source = discord.FFmpegPCMAudio(
            source=stdout,
            pipe=True,
            executable="ffmpeg",
            options=FFMPEG_OPTIONS,
        )

        # discord calls after= from its audio thread, so hand on_end back to the event loop
        def after(error: Exception | None) -> None:
            if error is not None:
                logger.warning(f"Playback ended with error: {error}")
            # FFmpeg is gone (track ended, skip, stop); yt-dlp would otherwise block on a full pipe
            stop_stream_process(downloader)
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


class DiscordSessionNotifier:
    """SessionNotifier that posts session messages to the session text channel."""

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
