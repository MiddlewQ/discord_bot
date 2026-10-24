import asyncio

from src.audio.track import Track
from src.audio.voice_session import EndReason, PlaybackError, PlaybackState, VoiceSession

TEXT_CHANNEL = 100
OTHER_CHANNEL = 200


def make_track(title: str) -> Track:
    return Track(title=title, webpage_url=f"https://youtu.be/{title}", duration=60)


class FakeConnection:
    """Behaves like discord's VoiceClient: is_playing() is False while paused."""

    def __init__(self, humans: int = 1, failing: tuple[str, ...] = ()):
        self.humans = humans
        self.failing = set(failing)
        self.playing = False
        self.paused = False
        self.played: list[str] = []
        self.disconnected = False
        self._on_end = None

    def is_playing(self) -> bool:
        return self.playing

    def is_paused(self) -> bool:
        return self.paused

    def human_count(self) -> int:
        return self.humans

    async def play(self, track, on_end) -> None:
        if track.title in self.failing:
            raise PlaybackError("refused")
        self.played.append(track.title)
        self.playing, self.paused = True, False
        self._on_end = on_end

    def pause(self) -> None:
        self.playing, self.paused = False, True

    def resume(self) -> None:
        self.playing, self.paused = True, False

    def stop(self) -> None:
        self.playing, self.paused = False, False

    async def disconnect(self) -> None:
        self.disconnected = True
        self.playing, self.paused = False, False

    async def finish(self, failure: str | None = None) -> None:
        """Simulate the current track ending, like discord calling the after= callback."""
        self.playing, self.paused = False, False
        on_end, self._on_end = self._on_end, None
        if on_end is not None:
            await on_end(failure)


class FakeTimer:
    def __init__(self):
        self.seconds: int | None = None
        self._callback = None

    @property
    def running(self) -> bool:
        return self._callback is not None

    def start(self, seconds, callback) -> None:
        self.seconds, self._callback = seconds, callback

    def cancel(self) -> None:
        self.seconds, self._callback = None, None

    async def fire(self) -> None:
        callback = self._callback
        self.cancel()
        assert callback is not None
        await callback()


class RecordingNotifier:
    def __init__(self):
        self.failed: list[tuple[str, str | None, int | None]] = []
        self.ended: list[tuple[EndReason, int | None]] = []

    async def track_failed(self, track, reason, text_channel_id) -> None:
        self.failed.append((track.title, reason, text_channel_id))

    async def session_ended(self, reason, text_channel_id) -> None:
        self.ended.append((reason, text_channel_id))


def attached_session(*titles: str, humans: int = 1, failing: tuple[str, ...] = ()):
    notifier, timer = RecordingNotifier(), FakeTimer()
    session = VoiceSession(notifier, timer)
    connection = FakeConnection(humans=humans, failing=failing)
    session.attach(connection, TEXT_CHANNEL)
    for title in titles:
        session.queue.enqueue(make_track(title))
    return session, connection, timer, notifier


# Connecting

def test_new_session_is_disconnected():
    session = VoiceSession(RecordingNotifier(), FakeTimer())

    assert session.state == PlaybackState.DISCONNECTED


def test_attach_while_idle_starts_idle_timeout():
    session, _, timer, _ = attached_session()

    assert session.state == PlaybackState.IDLE
    assert timer.seconds == 600


# Playback

def test_start_plays_first_track_and_cancels_timeout():
    session, connection, timer, _ = attached_session("a", "b")

    asyncio.run(session.start(TEXT_CHANNEL))

    assert connection.played == ["a"]
    assert session.state == PlaybackState.PLAYING
    assert session.queue.current == make_track("a")
    assert not timer.running


def test_start_while_playing_does_nothing():
    session, connection, _, _ = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(session.start(OTHER_CHANNEL))

    assert connection.played == ["a"]
    assert session.text_channel_id == TEXT_CHANNEL


def test_track_ending_plays_the_next_track():
    session, connection, _, _ = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(connection.finish())

    assert connection.played == ["a", "b"]
    assert session.queue.current == make_track("b")


def test_last_track_ending_starts_idle_timeout_and_keeps_connection():
    session, connection, timer, _ = attached_session("a")
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(connection.finish())

    assert session.state == PlaybackState.IDLE
    assert session.queue.is_empty
    assert timer.seconds == 600
    assert not connection.disconnected


def test_failed_track_is_reported_and_next_track_plays():
    session, connection, _, notifier = attached_session("a", "broken", "c", failing=("broken",))
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(connection.finish())

    assert notifier.failed == [("broken", "refused", TEXT_CHANNEL)]
    assert connection.played == ["a", "c"]


def test_unexpected_error_is_reported_without_a_reason():
    session, connection, _, notifier = attached_session("a")

    async def crash(track, on_end):
        raise ValueError("bug")

    connection.play = crash
    asyncio.run(session.start(TEXT_CHANNEL))

    assert notifier.failed == [("a", None, TEXT_CHANNEL)]


def test_failure_after_start_is_reported_and_next_track_plays():
    session, connection, _, notifier = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(connection.finish(failure="decode error"))

    assert notifier.failed == [("a", "decode error", TEXT_CHANNEL)]
    assert connection.played == ["a", "b"]


def test_normal_end_is_not_reported_as_failure():
    session, connection, _, notifier = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(connection.finish())

    assert notifier.failed == []


def test_all_tracks_failing_starts_idle_timeout():
    session, _, timer, notifier = attached_session("x", "y", failing=("x", "y"))

    asyncio.run(session.start(TEXT_CHANNEL))

    assert [title for title, _, _ in notifier.failed] == ["x", "y"]
    assert session.state == PlaybackState.IDLE
    assert timer.seconds == 600


# Commands

def test_pause_starts_paused_timeout_and_resume_cancels_it():
    session, _, timer, _ = attached_session("a")
    asyncio.run(session.start(TEXT_CHANNEL))

    session.pause()
    assert session.state == PlaybackState.PAUSED
    assert timer.seconds == 1800

    session.resume()
    assert session.state == PlaybackState.PLAYING
    assert not timer.running


def test_skip_returns_current_track_and_next_one_plays():
    session, connection, _, _ = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))

    skipped = session.skip()
    asyncio.run(connection.finish())

    assert skipped == make_track("a")
    assert connection.played == ["a", "b"]


def test_clear_while_playing_stops_and_then_idles():
    session, connection, timer, _ = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))

    session.clear()
    asyncio.run(connection.finish())

    assert session.queue.is_empty
    assert connection.played == ["a"]
    assert timer.seconds == 600


def test_clear_while_idle_starts_idle_timeout():
    session, _, timer, _ = attached_session("a")
    timer.cancel()

    session.clear()

    assert session.queue.is_empty
    assert timer.seconds == 600


# Timeouts

def test_no_humans_starts_no_humans_timeout():
    session, connection, timer, _ = attached_session("a")
    asyncio.run(session.start(TEXT_CHANNEL))

    connection.humans = 0
    session.on_members_changed()

    assert timer.seconds == 120


def test_humans_returning_restores_the_right_timeout():
    session, connection, timer, _ = attached_session("a", humans=0)
    asyncio.run(session.start(TEXT_CHANNEL))

    connection.humans = 1
    session.on_members_changed()
    assert not timer.running

    session.pause()
    timer.cancel()
    session.on_members_changed()
    assert timer.seconds == 1800


def test_timeout_ends_session_and_notifies_session_channel():
    session, connection, timer, notifier = attached_session("a")
    asyncio.run(session.start(TEXT_CHANNEL))
    asyncio.run(connection.finish())

    asyncio.run(timer.fire())

    assert notifier.ended == [(EndReason.IDLE, TEXT_CHANNEL)]
    assert connection.disconnected
    assert session.state == PlaybackState.DISCONNECTED


# Ending

def test_end_clears_everything():
    session, connection, timer, notifier = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(session.end(EndReason.STOPPED))

    assert notifier.ended == [(EndReason.STOPPED, TEXT_CHANNEL)]
    assert connection.disconnected
    assert session.queue.is_empty
    assert session.text_channel_id is None
    assert not timer.running


def test_track_ending_after_session_ended_plays_nothing():
    session, connection, timer, _ = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))
    asyncio.run(session.end(EndReason.STOPPED))

    asyncio.run(connection.finish())

    assert connection.played == ["a"]
    assert not timer.running



# Commands working on the session

def test_request_holds_the_timeout_until_it_finishes():
    session, _, timer, _ = attached_session()
    assert timer.seconds == 600

    session.begin_request()
    assert not timer.running
    session.clear()  # would normally restart the IDLE timeout
    assert not timer.running

    session.finish_request()
    assert timer.seconds == 600


def test_request_that_starts_playback_leaves_no_timeout():
    session, _, timer, _ = attached_session("a")

    session.begin_request()
    asyncio.run(session.start(TEXT_CHANNEL))
    session.finish_request()

    assert session.state == PlaybackState.PLAYING
    assert not timer.running


def test_request_while_paused_restarts_paused_timeout():
    session, _, timer, _ = attached_session("a")
    asyncio.run(session.start(TEXT_CHANNEL))
    session.pause()

    session.begin_request()
    session.finish_request()

    assert timer.seconds == 1800


def test_overlapping_requests_restart_timeout_only_after_the_last():
    session, _, timer, _ = attached_session()

    session.begin_request()
    session.begin_request()
    session.finish_request()
    assert not timer.running

    session.finish_request()
    assert timer.seconds == 600


def test_request_ending_the_session_leaves_no_timeout():
    session, _, timer, _ = attached_session("a")

    session.begin_request()
    asyncio.run(session.end(EndReason.STOPPED))
    session.finish_request()

    assert not timer.running


def test_end_count_changes_when_the_session_ends():
    session, _, _, _ = attached_session("a")
    before = session.end_count

    asyncio.run(session.end(EndReason.STOPPED))

    assert session.end_count != before
