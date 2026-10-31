from dataclasses import dataclass

from src.audio.track import Track


@dataclass(frozen=True)
class QueuedTrack:
    """An upcoming track with the number it keeps until it has played."""

    number: int
    track: Track


class TrackQueue:
    """The current track plus the upcoming tracks.

    Positions are 1-based indexes into the upcoming tracks, so they shift as tracks play; the
    current track has no position. Numbers identify a track instead: each enqueued track gets
    the next one, it never changes, and reset() is the only thing that reuses numbers.
    """

    def __init__(self):
        self._current: Track | None = None
        self._upcoming: list[QueuedTrack] = []
        self._last_number = 0

    @property
    def current(self) -> Track | None:
        return self._current

    @property
    def upcoming(self) -> tuple[Track, ...]:
        return tuple(queued.track for queued in self._upcoming)

    @property
    def numbered_upcoming(self) -> tuple[QueuedTrack, ...]:
        return tuple(self._upcoming)

    @property
    def is_empty(self) -> bool:
        return self._current is None and not self._upcoming

    @property
    def total_duration(self) -> int:
        """Full length of the current track plus all upcoming tracks, not the time remaining."""
        current = self._current.duration if self._current is not None else 0
        return current + sum(queued.track.duration for queued in self._upcoming)

    def enqueue(self, track: Track) -> int:
        """Add a track to the end of upcoming and return its position."""
        self._last_number += 1
        self._upcoming.append(QueuedTrack(self._last_number, track))
        return len(self._upcoming)

    def advance(self) -> Track | None:
        """Make the next upcoming track current and return it, or None when upcoming is empty."""
        self._current = self._upcoming.pop(0).track if self._upcoming else None
        return self._current

    def remove(self, position: int) -> Track | None:
        """Remove and return the track at position, or None if the position is out of range."""
        if position < 1 or position > len(self._upcoming):
            return None
        return self._upcoming.pop(position - 1).track

    def remove_number(self, number: int) -> Track | None:
        """Remove and return the upcoming track with this number, or None if there is none."""
        for index, queued in enumerate(self._upcoming):
            if queued.number == number:
                return self._upcoming.pop(index).track
        return None

    def clear(self) -> None:
        """Empty the queue but keep counting, so a number seen earlier can't mean a new track."""
        self._current = None
        self._upcoming.clear()

    def reset(self) -> None:
        """Empty the queue and restart numbers at 1, for a new session."""
        self.clear()
        self._last_number = 0

    def time_until(self, position: int) -> int:
        """Estimated seconds until the track at position starts, counting the full current track."""
        current = self._current.duration if self._current is not None else 0
        return current + sum(queued.track.duration for queued in self._upcoming[:position - 1])
