import asyncio

import pytest
from yt_dlp.utils import DownloadError

from src.audio.track import Track
from src.bot.track_resolver import LookupFailure, TrackResolver

THIRTY_MINUTES = 1800


def entry(title="Song", url="https://www.youtube.com/watch?v=abc", duration=200, **extra):
    return {"title": title, "webpage_url": url, "duration": duration, **extra}


def resolve(query: str, answer=None, error: Exception | None = None):
    """Resolve with a fake yt-dlp that returns `answer` or raises `error`; also returns what it was asked."""
    asked = []

    def fake_extract(search_query):
        asked.append(search_query)
        if error is not None:
            raise error
        return answer

    result = asyncio.run(TrackResolver(max_seconds=THIRTY_MINUTES, extract=fake_extract).resolve(query))
    return result, asked


def test_search_text_becomes_a_youtube_search_and_takes_the_first_result():
    result, asked = resolve("silver scrapes", {"entries": [entry("First"), entry("Second")]})

    assert asked == ["ytsearch1:silver scrapes"]
    assert result == Track(title="First", webpage_url="https://www.youtube.com/watch?v=abc", duration=200)


def test_url_is_looked_up_directly():
    result, asked = resolve("https://youtu.be/abc", entry("From URL"))

    assert asked == ["https://youtu.be/abc"]
    assert isinstance(result, Track) and result.title == "From URL"


def test_missing_title_and_duration_get_defaults():
    result, _ = resolve("x", {"entries": [{"webpage_url": "https://youtu.be/abc"}]})

    assert result == Track(title="Unknown title", webpage_url="https://youtu.be/abc", duration=0)


def test_original_url_is_used_when_webpage_url_is_missing():
    result, _ = resolve("x", {"entries": [{"original_url": "https://youtu.be/orig", "title": "T"}]})

    assert isinstance(result, Track) and result.webpage_url == "https://youtu.be/orig"


@pytest.mark.parametrize("thumbnails, expected", [
    ({"thumbnail": "direct.jpg"}, "direct.jpg"),
    ({"thumbnails": [{"url": "first.jpg"}, {"url": "last.jpg"}]}, "first.jpg"),
    ({"thumbnails": ["broken", {"url": "last.jpg"}]}, "last.jpg"),
    ({"thumbnails": []}, None),
    ({}, None),
])
def test_thumbnail_fallbacks(thumbnails, expected):
    result, _ = resolve("x", {"entries": [entry(**thumbnails)]})

    assert isinstance(result, Track) and result.thumbnail == expected


@pytest.mark.parametrize("answer", [
    None,
    "not a dict",
    {"entries": []},
    {"entries": ["not a dict"]},
    {"entries": [{"title": "No URL"}]},
])
def test_unusable_answers_mean_not_found(answer):
    result, _ = resolve("x", answer)

    assert result == LookupFailure.NOT_FOUND


def test_tracks_up_to_the_limit_are_accepted():
    result, _ = resolve("lofi", {"entries": [entry(duration=THIRTY_MINUTES)]})

    assert isinstance(result, Track)


def test_tracks_over_the_limit_are_too_long():
    result, _ = resolve("lofi", {"entries": [entry(duration=THIRTY_MINUTES + 1)]})

    assert result == LookupFailure.TOO_LONG


@pytest.mark.parametrize("error_text, expected", [
    ("ERROR: [youtube] abc: This video is not available", LookupFailure.UNAVAILABLE),
    ("ERROR: Sign in to confirm your age", LookupFailure.AGE_RESTRICTED),
    ("ERROR: This video may be inappropriate for some users", LookupFailure.AGE_RESTRICTED),
    ("ERROR: No supported JavaScript runtime could be found", LookupFailure.NO_JS_RUNTIME),
    ("ERROR: something new from YouTube", LookupFailure.YTDLP_ERROR),
])
def test_ytdlp_errors_map_to_reasons(error_text, expected):
    result, _ = resolve("x", error=DownloadError(error_text))

    assert result == expected


def test_unexpected_errors_are_ytdlp_errors():
    result, _ = resolve("x", error=ValueError("bug"))

    assert result == LookupFailure.YTDLP_ERROR
