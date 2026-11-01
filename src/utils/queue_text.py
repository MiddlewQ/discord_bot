from discord.utils import escape_markdown

from src.audio.track_queue import QueuedTrack
import src.utils.message as msg
from src.utils.time_conversion import format_track_length

# Long enough for most titles, short enough to stay on one line beside the thumbnail on a computer
MAX_TITLE_LENGTH = 45


def shorten_title(title: str) -> str:
    """Cut a long title so it ends in "…" and is at most MAX_TITLE_LENGTH characters."""
    if len(title) <= MAX_TITLE_LENGTH:
        return title
    return title[:MAX_TITLE_LENGTH - 1].rstrip() + "…"


def format_queue_line(queued: QueuedTrack) -> str:
    """One row of !queue. Shortens before escaping, so a cut can't split an escaped character."""
    return msg.QUEUE_LINE.format(
        number=queued.number,
        title=escape_markdown(shorten_title(queued.track.title)),
        length=format_track_length(queued.track.duration),
    )
