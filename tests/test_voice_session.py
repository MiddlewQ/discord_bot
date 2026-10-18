import asyncio

from src.audio.track import Track
from src.audio.voice_session import EndReason, PlaybackState, VoiceSession

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
            raise RuntimeError("no stream URL")
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

    async def finish(self) -> None:
        """Simulate the current track ending, like discord calling the after= callback."""
        self.playing, self.paused = False, False
        on_end, self._on_end = self._on_end, None
        if on_end is not None:
            await on_end()


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


class RecordingListener:
    def __init__(self):
        self.failed: list[tuple[str, int | None]] = []
        self.ended: list[tuple[EndReason, int | None]] = []

    async def track_failed(self, track, text_channel_id) -> None:
        self.failed.append((track.title, text_channel_id))

    async def session_ended(self, reason, text_channel_id) -> None:
        self.ended.append((reason, text_channel_id))


def attached_session(*titles: str, humans: int = 1, failing: tuple[str, ...] = ()):
    listener, timer = RecordingListener(), FakeTimer()
    session = VoiceSession(listener, timer)
    connection = FakeConnection(humans=humans, failing=failing)
    session.attach(connection, TEXT_CHANNEL)
    for title in titles:
        session.queue.enqueue(make_track(title))
    return session, connection, timer, listener


# Connecting

def test_new_session_is_disconnected():
    session = VoiceSession(RecordingListener(), FakeTimer())

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
    session, connection, _, listener = attached_session("a", "broken", "c", failing=("broken",))
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(connection.finish())

    assert listener.failed == [("broken", TEXT_CHANNEL)]
    assert connection.played == ["a", "c"]


def test_all_tracks_failing_starts_idle_timeout():
    session, _, timer, listener = attached_session("x", "y", failing=("x", "y"))

    asyncio.run(session.start(TEXT_CHANNEL))

    assert [title for title, _ in listener.failed] == ["x", "y"]
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


# Text channel lock

def test_commands_only_accepted_from_session_channel_while_playing():
    session, _, _, _ = attached_session("a")
    assert session.accepts_commands_from(OTHER_CHANNEL)

    asyncio.run(session.start(TEXT_CHANNEL))

    assert session.accepts_commands_from(TEXT_CHANNEL)
    assert not session.accepts_commands_from(OTHER_CHANNEL)


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
    session, connection, timer, listener = attached_session("a")
    asyncio.run(session.start(TEXT_CHANNEL))
    asyncio.run(connection.finish())

    asyncio.run(timer.fire())

    assert listener.ended == [(EndReason.IDLE, TEXT_CHANNEL)]
    assert connection.disconnected
    assert session.state == PlaybackState.DISCONNECTED


# Ending

def test_end_clears_everything():
    session, connection, timer, listener = attached_session("a", "b")
    asyncio.run(session.start(TEXT_CHANNEL))

    asyncio.run(session.end(EndReason.STOPPED))

    assert listener.ended == [(EndReason.STOPPED, TEXT_CHANNEL)]
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
