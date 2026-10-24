import asyncio
import sys

import pytest

from src.bot.playback import start_stream_process, stop_stream_process


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
