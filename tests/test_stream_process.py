import asyncio
import subprocess
import sys
import tempfile

import pytest

from src.audio.track import Track
from src.bot.playback import DiscordVoiceConnection, describe_stream_error, start_stream_process, stop_stream_process
import src.utils.message as msg

TRACK = Track(title="Song", webpage_url="https://youtu.be/x", duration=60)


def python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_returns_process_once_output_arrives_without_consuming_it():
    async def scenario():
        process = await start_stream_process(python("import sys; sys.stdout.write('audio')"), timeout=10)
        assert process.stdout is not None
        data = process.stdout.read()
        stop_stream_process(process)
        return data

    assert asyncio.run(scenario()) == b"audio"


def test_raises_with_last_error_line_when_process_exits_without_output():
    code = "import sys; sys.stderr.write('WARNING: x\\nERROR: HTTP Error 403: Forbidden\\n'); sys.exit(1)"

    with pytest.raises(RuntimeError, match="HTTP Error 403"):
        asyncio.run(start_stream_process(python(code), timeout=10))


def test_raises_when_no_output_within_timeout():
    with pytest.raises(RuntimeError, match="No audio"):
        asyncio.run(start_stream_process(python("import time; time.sleep(30)"), timeout=0.5))


def test_describe_stream_error_maps_known_failures():
    assert describe_stream_error("ERROR: unable to download video data: HTTP Error 403: Forbidden") == msg.PLAYBACK_FAIL_FORBIDDEN
    assert describe_stream_error("ERROR: [youtube] abc: This video is unavailable") == msg.PLAYBACK_FAIL_UNAVAILABLE
    assert describe_stream_error("No audio after 30 seconds") == msg.PLAYBACK_FAIL_TIMEOUT
    assert describe_stream_error("something new") == msg.PLAYBACK_FAIL_UNKNOWN


def finished_process(code: str) -> subprocess.Popen:
    process = subprocess.Popen(python(code), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.wait()
    return process


def errors_file(text: str):
    file = tempfile.TemporaryFile()
    file.write(text.encode())
    return file


def test_normal_end_is_not_a_failure():
    downloader = finished_process("pass")

    assert DiscordVoiceConnection._playback_failure(TRACK, None, errors_file(""), downloader) is None


def test_ffmpeg_errors_mean_the_audio_could_not_be_decoded():
    downloader = finished_process("pass")

    failure = DiscordVoiceConnection._playback_failure(TRACK, None, errors_file("Invalid data found"), downloader)

    assert failure == msg.PLAYBACK_FAIL_DECODE


def test_ytdlp_failing_mid_stream_is_reported_with_its_reason():
    downloader = finished_process("import sys; sys.stderr.write('ERROR: HTTP Error 403: Forbidden'); sys.exit(1)")

    failure = DiscordVoiceConnection._playback_failure(TRACK, None, errors_file(""), downloader)

    assert failure == msg.PLAYBACK_FAIL_FORBIDDEN


def test_skip_while_ytdlp_still_runs_is_not_a_failure():
    downloader = subprocess.Popen(python("import time; time.sleep(30)"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert DiscordVoiceConnection._playback_failure(TRACK, None, errors_file(""), downloader) is None
    finally:
        stop_stream_process(downloader)
