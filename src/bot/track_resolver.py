"""Find the YouTube track for a search text or URL, using yt-dlp."""

import asyncio
from collections.abc import Callable
from enum import StrEnum, auto
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from src.audio.track import Track
from src.bot.playback import YTDLP_AUDIO_FORMAT
import logging
import src.utils.message as msg

logger = logging.getLogger(__name__)


class LookupFailure(StrEnum):
    NOT_FOUND = auto()
    UNAVAILABLE = auto()
    AGE_RESTRICTED = auto()
    NO_JS_RUNTIME = auto()
    YTDLP_ERROR = auto()
    TOO_LONG = auto()


def youtube_extract() -> Callable[[str], Any]:
    """yt-dlp's metadata lookup, without downloading; the default for TrackResolver."""
    options: Any = {"format": YTDLP_AUDIO_FORMAT, "noplaylist": True, "quiet": True}

    # A new YoutubeDL for each lookup, because searches can run at the same time and one object
    # can't handle that: it sees a second identical search as a repeat and returns None for it
    return lambda query: YoutubeDL(options).extract_info(query, download=False)


class TrackResolver:
    """Turns what a user typed into a playable Track, or the reason it can't be queued."""

    def __init__(self, max_seconds: int, extract: Callable[[str], Any] | None = None):
        # extract does the actual lookup: yt-dlp in the bot, a fake returning prepared answers in tests
        self.max_seconds = max_seconds
        self._extract = extract or youtube_extract()

    async def resolve(self, query: str) -> Track | LookupFailure:
        search_query = query if query.startswith("http") else f"ytsearch1:{query}"
        loop = asyncio.get_running_loop()

        try:
            info = await loop.run_in_executor(None, self._extract, search_query)
        except (DownloadError, ExtractorError) as error:
            return self._classify_error(query, error)
        except Exception:
            logger.exception(msg.LOG_YTDLP_FAILED_UNEXPECTED.format(query=query))
            return LookupFailure.YTDLP_ERROR

        track = self._parse(query, info)

        if isinstance(track, Track) and track.duration > self.max_seconds:
            logger.info(msg.LOG_TRACK_TOO_LONG.format(query=query, title=track.title, minutes=track.duration // 60))
            return LookupFailure.TOO_LONG

        return track

    def _classify_error(self, query: str, error: Exception) -> LookupFailure:
        error_text = str(error).lower()

        if "this video is not available" in error_text:
            logger.warning(msg.LOG_YTDLP_FAILED_UNAVAILABLE.format(query=query, error=error))
            return LookupFailure.UNAVAILABLE

        if (
            "sign in to confirm your age" in error_text
            or "age-restricted" in error_text
            or "this video may be inappropriate" in error_text
        ):
            logger.warning(msg.LOG_YTDLP_FAILED_AGE_RESTRICTED.format(query=query, error=error))
            return LookupFailure.AGE_RESTRICTED

        if (
            "no supported javascript runtime" in error_text
            or ("javascript runtime" in error_text and "deno" in error_text)
        ):
            logger.warning(msg.LOG_YTDLP_FAILED_RUNTIME.format(query=query, error=error))
            return LookupFailure.NO_JS_RUNTIME

        logger.warning(msg.LOG_YTDLP_FAILED_EXTRACTION.format(query=query, error=error))
        return LookupFailure.YTDLP_ERROR

    def _parse(self, query: str, info: Any) -> Track | LookupFailure:
        if not isinstance(info, dict):
            logger.warning(msg.LOG_YTDLP_RESULT_INVALID.format(query=query, result_type=type(info).__name__))
            return LookupFailure.NOT_FOUND

        # A search returns a list of entries; a URL returns the video itself
        entries = info.get("entries")
        if isinstance(entries, list):
            if not entries:
                logger.warning(msg.LOG_YTDLP_RESULT_EMPTY.format(query=query))
                return LookupFailure.NOT_FOUND
            entry = entries[0]
        else:
            entry = info

        if not isinstance(entry, dict):
            logger.warning(msg.LOG_YTDLP_ENTRY_INVALID.format(query=query, entry_type=type(entry).__name__))
            return LookupFailure.NOT_FOUND

        webpage_url = entry.get("webpage_url") or entry.get("original_url")
        if not isinstance(webpage_url, str) or not webpage_url:
            logger.warning(msg.LOG_YTDLP_ENTRY_MISSING_URL.format(query=query))
            return LookupFailure.NOT_FOUND

        return Track(
            title=entry.get("title") or "Unknown title",
            webpage_url=webpage_url,
            duration=int(entry.get("duration") or 0),
            thumbnail=self._thumbnail(entry),
        )

    @staticmethod
    def _thumbnail(entry: dict) -> str | None:
        thumbnail = entry.get("thumbnail")
        if thumbnail:
            return thumbnail

        thumbnails = entry.get("thumbnails") or []
        if not isinstance(thumbnails, list) or not thumbnails:
            return None

        first, last = thumbnails[0], thumbnails[-1]
        first_url = first.get("url") if isinstance(first, dict) else None
        last_url = last.get("url") if isinstance(last, dict) else None
        return first_url or last_url
