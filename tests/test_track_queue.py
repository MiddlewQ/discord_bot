from src.audio.track import Track
from src.audio.track_queue import TrackQueue


def make_track(title: str, duration: int = 60) -> Track:
    return Track(title=title, webpage_url=f"https://youtu.be/{title}", duration=duration)


def test_new_queue_is_empty():
    queue = TrackQueue()

    assert queue.is_empty
    assert queue.current is None
    assert queue.upcoming == ()
    assert queue.total_duration == 0


def test_enqueue_returns_position_in_upcoming():
    queue = TrackQueue()

    assert queue.enqueue(make_track("a")) == 1
    assert queue.enqueue(make_track("b")) == 2
    assert [track.title for track in queue.upcoming] == ["a", "b"]


def test_advance_moves_next_upcoming_to_current():
    queue = TrackQueue()
    a, b = make_track("a"), make_track("b")
    queue.enqueue(a)
    queue.enqueue(b)

    assert queue.advance() == a
    assert queue.current == a
    assert queue.upcoming == (b,)


def test_advance_on_empty_upcoming_clears_current():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.advance()

    assert queue.advance() is None
    assert queue.current is None
    assert queue.is_empty


def test_remove_by_position():
    queue = TrackQueue()
    a, b, c = make_track("a"), make_track("b"), make_track("c")
    for track in (a, b, c):
        queue.enqueue(track)

    assert queue.remove(2) == b
    assert queue.upcoming == (a, c)


def test_remove_out_of_range_returns_none():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))

    assert queue.remove(0) is None
    assert queue.remove(2) is None
    assert len(queue.upcoming) == 1


def test_remove_does_not_touch_current():
    queue = TrackQueue()
    a = make_track("a")
    queue.enqueue(a)
    queue.advance()

    assert queue.remove(1) is None
    assert queue.current == a


def test_total_duration_counts_current_and_upcoming():
    queue = TrackQueue()
    queue.enqueue(make_track("a", 100))
    queue.enqueue(make_track("b", 200))
    queue.enqueue(make_track("c", 300))
    assert queue.total_duration == 600

    queue.advance()
    assert queue.total_duration == 600

    queue.remove(2)
    assert queue.total_duration == 300

    queue.advance()
    assert queue.total_duration == 200

    queue.advance()
    assert queue.total_duration == 0


def test_clear_empties_current_and_upcoming():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.enqueue(make_track("b"))
    queue.advance()

    queue.clear()

    assert queue.is_empty
    assert queue.total_duration == 0


def test_time_until_counts_current_and_tracks_ahead():
    queue = TrackQueue()
    queue.enqueue(make_track("a", 100))
    queue.enqueue(make_track("b", 200))
    queue.enqueue(make_track("c", 300))
    queue.advance()  # a is current

    assert queue.time_until(1) == 100
    assert queue.time_until(2) == 300


def test_time_until_with_nothing_playing():
    queue = TrackQueue()
    queue.enqueue(make_track("a", 100))
    queue.enqueue(make_track("b", 200))

    assert queue.time_until(1) == 0
    assert queue.time_until(2) == 100
