import pytest

from src.audio.voice_session import PlaybackState
from src.bot.admission import CommandRequest, Needs, Reject, check

SESSION_TEXT = 10
OTHER_TEXT = 11
BOT_VOICE = 20
OTHER_VOICE = 21

DISCONNECTED = PlaybackState.DISCONNECTED
IDLE = PlaybackState.IDLE
PLAYING = PlaybackState.PLAYING
PAUSED = PlaybackState.PAUSED


def request(
    needs: Needs,
    state: PlaybackState,
    text: int = SESSION_TEXT,
    user_voice: int | None = BOT_VOICE,
    bot_voice: int | None = BOT_VOICE,
    session_text: int | None = SESSION_TEXT,
) -> CommandRequest:
    if state == DISCONNECTED:
        bot_voice, session_text = None, None
    return CommandRequest(
        needs=needs,
        author_id=1,
        text_channel_id=text,
        user_voice_channel_id=user_voice,
        bot_voice_channel_id=bot_voice,
        session_state=state,
        session_text_channel_id=session_text,
    )


@pytest.mark.parametrize("case, expected", [
    # Text channel lock, for every kind of command
    (request(Needs.SESSION_CHANNEL, PLAYING, text=OTHER_TEXT), Reject.WRONG_TEXT_CHANNEL),
    (request(Needs.SESSION_CHANNEL, IDLE, text=OTHER_TEXT), Reject.WRONG_TEXT_CHANNEL),
    (request(Needs.SAME_VOICE, PAUSED, text=OTHER_TEXT), Reject.WRONG_TEXT_CHANNEL),
    (request(Needs.CAN_CONNECT, IDLE, text=OTHER_TEXT), Reject.WRONG_TEXT_CHANNEL),
    (request(Needs.CAN_CONNECT, DISCONNECTED, text=OTHER_TEXT), None),
    (request(Needs.SESSION_CHANNEL, DISCONNECTED, text=OTHER_TEXT), None),

    # SESSION_CHANNEL only cares about the text channel
    (request(Needs.SESSION_CHANNEL, PLAYING, user_voice=None), None),

    # SAME_VOICE: bot and user in the same voice channel
    (request(Needs.SAME_VOICE, PLAYING), None),
    (request(Needs.SAME_VOICE, IDLE), None),
    (request(Needs.SAME_VOICE, DISCONNECTED), Reject.BOT_NOT_IN_VOICE),
    (request(Needs.SAME_VOICE, DISCONNECTED, user_voice=None), Reject.BOT_NOT_IN_VOICE),
    (request(Needs.SAME_VOICE, PLAYING, user_voice=None), Reject.USER_NOT_IN_VOICE),
    (request(Needs.SAME_VOICE, PAUSED, user_voice=OTHER_VOICE), Reject.BOT_IN_OTHER_CHANNEL),
    (request(Needs.SAME_VOICE, IDLE, user_voice=OTHER_VOICE), Reject.BOT_IN_OTHER_CHANNEL),

    # CAN_CONNECT: user in voice; the bot may join or move unless it is busy elsewhere
    (request(Needs.CAN_CONNECT, DISCONNECTED), None),
    (request(Needs.CAN_CONNECT, DISCONNECTED, user_voice=None), Reject.USER_NOT_IN_VOICE),
    (request(Needs.CAN_CONNECT, IDLE, user_voice=OTHER_VOICE), None),
    (request(Needs.CAN_CONNECT, PLAYING), None),
    (request(Needs.CAN_CONNECT, PLAYING, user_voice=OTHER_VOICE), Reject.BOT_BUSY_ELSEWHERE),
    (request(Needs.CAN_CONNECT, PAUSED, user_voice=OTHER_VOICE), Reject.BOT_BUSY_ELSEWHERE),
    (request(Needs.CAN_CONNECT, PLAYING, user_voice=None), Reject.USER_NOT_IN_VOICE),
    (request(Needs.CAN_CONNECT, PLAYING, bot_voice=None), Reject.BOT_NOT_IN_VOICE),
])
def test_check(case, expected):
    assert check(case) == expected
