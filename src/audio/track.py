from dataclasses import dataclass

@dataclass(frozen=True)
class Track:
    """One playable YouTube video, as found by a search or URL."""

    title: str        # "Unknown title" if yt-dlp gave none
    webpage_url: str  # page URL, not the stream URL; the stream is fetched again at play time
    duration: int     # seconds, 0 if unknown
    thumbnail: str | None = None
