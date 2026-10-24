"""Who may run a command, and where. Only the rules: no discord, so they can be tested as a table."""

from dataclasses import dataclass
from enum import StrEnum, auto

from src.audio.voice_session import PlaybackState


class Needs(StrEnum):
    SESSION_CHANNEL = auto()  # queue, playing, status: only the text channel rule
    SAME_VOICE = auto()       # pause, resume, skip, remove, clear, stop: user and bot in one voice channel
    CAN_CONNECT = auto()      # join, play, multiplay: the bot may connect or move to the user


class Reject(StrEnum):
    WRONG_TEXT_CHANNEL = auto()
    USER_NOT_IN_VOICE = auto()
    BOT_NOT_IN_VOICE = auto()
    BOT_IN_OTHER_CHANNEL = auto()
    BOT_BUSY_ELSEWHERE = auto()


@dataclass(frozen=True)
class CommandRequest:
    """Everything the rules need to know about one command; new rules add fields here."""

    needs: Needs
    author_id: int
    text_channel_id: int
    user_voice_channel_id: int | None
    bot_voice_channel_id: int | None
    session_state: PlaybackState
    session_text_channel_id: int | None


def check(request: CommandRequest) -> Reject | None:
    """Why the command may not run, or None if it may."""
    connected = request.session_state != PlaybackState.DISCONNECTED
    busy = request.session_state in (PlaybackState.PLAYING, PlaybackState.PAUSED)

    # The session text channel is locked while connected; a disconnected bot takes commands anywhere
    if (
        connected
        and request.session_text_channel_id is not None
        and request.text_channel_id != request.session_text_channel_id
    ):
        return Reject.WRONG_TEXT_CHANNEL

    if request.needs == Needs.SESSION_CHANNEL:
        return None

    if request.needs == Needs.SAME_VOICE:
        if not connected or request.bot_voice_channel_id is None:
            return Reject.BOT_NOT_IN_VOICE
        if request.user_voice_channel_id is None:
            return Reject.USER_NOT_IN_VOICE
        if request.user_voice_channel_id != request.bot_voice_channel_id:
            return Reject.BOT_IN_OTHER_CHANNEL
        return None

    # CAN_CONNECT: an idle bot in another channel moves to the user, a busy one doesn't
    if request.user_voice_channel_id is None:
        return Reject.USER_NOT_IN_VOICE
    if busy and request.bot_voice_channel_id is None:
        return Reject.BOT_NOT_IN_VOICE
    if busy and request.user_voice_channel_id != request.bot_voice_channel_id:
        return Reject.BOT_BUSY_ELSEWHERE
    return None
