import discord

from enum import StrEnum, auto
from dataclasses import dataclass

from src.audio.voice_session import PlaybackState

@dataclass(frozen=True)
class VoiceContext:
    state: PlaybackState
    vc: discord.VoiceClient | None
    user_channel: discord.VoiceChannel | discord.StageChannel | None


class VoiceChannelReject(StrEnum):
    BOT_NOT_CONNECTED  = auto()
    USER_NOT_CONNECTED = auto()
    DIFFERENT_VOICE_CHANNEL = auto()
