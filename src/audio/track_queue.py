from src.audio.track import Track

class TrackQueue:
    """The current track plus the upcoming tracks.

    Positions are 1-based indexes into the upcoming tracks; the current track has no position.
    """

    def __init__(self):
        self._current: Track | None = None
        self._upcoming: list[Track] = []

    @property
    def current(self) -> Track | None:
        return self._current

    @property
    def upcoming(self) -> tuple[Track, ...]:
        return tuple(self._upcoming)

    @property
    def is_empty(self) -> bool:
        return self._current is None and not self._upcoming

    @property
    def total_duration(self) -> int:
        """Full length of the current track plus all upcoming tracks, not the time remaining."""
        current = self._current.duration if self._current is not None else 0
        return current + sum(track.duration for track in self._upcoming)

    def enqueue(self, track: Track) -> int:
        """Add a track to the end of upcoming and return its position."""
        self._upcoming.append(track)
        return len(self._upcoming)

    def advance(self) -> Track | None:
        """Make the next upcoming track current and return it, or None when upcoming is empty."""
        self._current = self._upcoming.pop(0) if self._upcoming else None
        return self._current

    def remove(self, position: int) -> Track | None:
        """Remove and return the track at position, or None if the position is out of range."""
        if position < 1 or position > len(self._upcoming):
            return None
        return self._upcoming.pop(position - 1)

    def clear(self) -> None:
        self._current = None
        self._upcoming.clear()

    def time_until(self, position: int) -> int:
        """Estimated seconds until the track at position starts, counting the full current track."""
        current = self._current.duration if self._current is not None else 0
        return current + sum(track.duration for track in self._upcoming[:position - 1])
