from src.audio.track import Track
from src.audio.track_queue import Placement, QueuedTrack, TrackQueue


def make_track(title: str, duration: int = 60) -> Track:
    return Track(title=title, webpage_url=f"https://youtu.be/{title}", duration=duration)


def test_new_queue_is_empty():
    queue = TrackQueue()

    assert queue.is_empty
    assert queue.current is None
    assert queue.upcoming == ()
    assert queue.total_duration == 0


def test_enqueue_returns_number_and_position():
    queue = TrackQueue()

    assert queue.enqueue(make_track("a")) == Placement(number=1, position=1)
    assert queue.enqueue(make_track("b")) == Placement(number=2, position=2)
    assert [track.title for track in queue.upcoming] == ["a", "b"]


def test_number_and_position_differ_once_tracks_have_played():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.enqueue(make_track("b"))
    queue.advance()
    queue.advance()

    assert queue.enqueue(make_track("c")) == Placement(number=3, position=1)


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


def test_total_duration_counts_current_and_upcoming():
    queue = TrackQueue()
    queue.enqueue(make_track("a", 100))
    queue.enqueue(make_track("b", 200))
    queue.enqueue(make_track("c", 300))
    assert queue.total_duration == 600

    queue.advance()
    assert queue.total_duration == 600

    queue.remove_number(3)
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


def numbers(queue: TrackQueue) -> list[int]:
    return [queued.number for queued in queue.numbered_upcoming]


def test_numbers_count_up_from_one():
    queue = TrackQueue()
    a, b = make_track("a"), make_track("b")
    queue.enqueue(a)
    queue.enqueue(b)

    assert queue.numbered_upcoming == (QueuedTrack(1, a), QueuedTrack(2, b))


def test_numbers_stay_the_same_as_tracks_play():
    queue = TrackQueue()
    for title in ("a", "b", "c"):
        queue.enqueue(make_track(title))

    queue.advance()
    queue.advance()

    assert numbers(queue) == [3]


def test_numbers_are_not_reused_after_tracks_leave_the_queue():
    queue = TrackQueue()
    for title in ("a", "b", "c"):
        queue.enqueue(make_track(title))
    queue.advance()  # a played, 1 is gone
    queue.remove_number(3)

    queue.enqueue(make_track("d"))

    assert numbers(queue) == [2, 4]


def test_remove_number_tells_identical_tracks_apart():
    queue = TrackQueue()
    for title in ("a", "same", "same"):
        queue.enqueue(make_track(title))
    queue.advance()

    assert queue.remove_number(3) == make_track("same")
    assert numbers(queue) == [2]


def test_remove_number_without_a_match_returns_none():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.enqueue(make_track("b"))
    queue.advance()  # a is current, so number 1 can no longer be removed

    assert queue.remove_number(1) is None
    assert queue.remove_number(3) is None
    assert queue.current == make_track("a")
    assert numbers(queue) == [2]


def test_position_of_follows_the_track_as_the_queue_moves():
    queue = TrackQueue()
    for title in ("a", "b", "c"):
        queue.enqueue(make_track(title))

    assert queue.position_of(3) == 3
    queue.advance()
    assert queue.position_of(3) == 2


def test_position_of_a_track_not_waiting_is_none():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.advance()  # a is current, so it is no longer waiting

    assert queue.position_of(1) is None
    assert queue.position_of(2) is None


def test_current_track_keeps_its_number():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.enqueue(make_track("b"))
    assert queue.current_number is None

    queue.advance()
    assert queue.current_number == 1

    queue.advance()
    assert queue.current_number == 2


def test_current_number_is_gone_when_nothing_is_current():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.advance()

    queue.advance()
    assert queue.current_number is None

    queue.enqueue(make_track("b"))
    queue.advance()
    queue.clear()
    assert queue.current_number is None


def test_clear_keeps_counting():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.enqueue(make_track("b"))

    queue.clear()
    queue.enqueue(make_track("c"))

    assert numbers(queue) == [3]


def test_reset_empties_the_queue_and_restarts_numbers():
    queue = TrackQueue()
    queue.enqueue(make_track("a"))
    queue.enqueue(make_track("b"))
    queue.advance()

    queue.reset()

    assert queue.is_empty
    queue.enqueue(make_track("c"))
    assert numbers(queue) == [1]


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
