import discord

from enum import StrEnum, auto
from dataclasses import dataclass
import src.utils.message as msg

@dataclass
class QueueEntry:
    track: dict

class PlaybackState(StrEnum):
    DISCONNECTED = auto()
    IDLE = auto()
    PLAYING = auto()
    PAUSED = auto()

@dataclass(frozen=True)
class VoiceContext:
    state: PlaybackState
    vc: discord.VoiceClient | None
    user_channel: discord.VoiceChannel | discord.StageChannel | None


class TextChannelReject(StrEnum):
    WRONG_TEXT_CHANNEL = auto()
    
class VoiceChannelReject(StrEnum):
    BOT_NOT_CONNECTED  = auto()
    USER_NOT_CONNECTED = auto()
    DIFFERENT_VOICE_CHANNEL = auto()

@dataclass(frozen=True)
class TimeoutPolicy:
    seconds: int
    discord_message: str
    log_message: str

class TimeoutReason(StrEnum):
    NO_HUMANS = auto()
    IDLE = auto()
    PAUSED = auto()


TIMEOUT_POLICIES = {
    TimeoutReason.NO_HUMANS: TimeoutPolicy(
        seconds = 120,
        discord_message=msg.TIMEOUT_NO_HUMANS,
        log_message=msg.LOG_TIMEOUT_NO_HUMANS,
    ),
    TimeoutReason.IDLE: TimeoutPolicy(
        seconds=600,
        discord_message=msg.TIMEOUT_IDLE,
        log_message=msg.LOG_TIMEOUT_IDLE,
    ),
    TimeoutReason.PAUSED: TimeoutPolicy(
        seconds=1800,
        discord_message=msg.TIMEOUT_PAUSED,
        log_message=msg.LOG_TIMEOUT_PAUSED
    ),
}