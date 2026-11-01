from src.audio.track import Track
from src.audio.track_queue import QueuedTrack
from src.utils.queue_text import MAX_TITLE_LENGTH, format_queue_line, shorten_title


def make_queued(title: str, number: int = 7, duration: int = 249) -> QueuedTrack:
    return QueuedTrack(number, Track(title=title, webpage_url="https://youtu.be/a", duration=duration))


def test_short_title_is_unchanged():
    title = "a" * MAX_TITLE_LENGTH

    assert shorten_title(title) == title


def test_long_title_is_cut_to_the_limit():
    shortened = shorten_title("a" * (MAX_TITLE_LENGTH + 1))

    assert len(shortened) == MAX_TITLE_LENGTH
    assert shortened.endswith("…")


def test_queue_line_shows_number_title_and_length():
    assert format_queue_line(make_queued("Houdini")) == "`#7` Houdini · 4:09"


def test_queue_line_escapes_discord_formatting_in_titles():
    assert format_queue_line(make_queued("*NSYNC")) == "`#7` \\*NSYNC · 4:09"
