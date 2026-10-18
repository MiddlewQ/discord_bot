import asyncio

from src.cogs.discord_playback import AsyncioTimer


def test_callback_runs_after_delay():
    calls = []

    async def scenario():
        timer = AsyncioTimer()

        async def callback():
            calls.append("fired")

        timer.start(0, callback)
        await asyncio.sleep(0.01)

    asyncio.run(scenario())

    assert calls == ["fired"]


def test_cancel_stops_callback():
    calls = []

    async def scenario():
        timer = AsyncioTimer()

        async def callback():
            calls.append("fired")

        timer.start(0, callback)
        timer.cancel()
        await asyncio.sleep(0.01)

    asyncio.run(scenario())

    assert calls == []


def test_start_replaces_running_timeout():
    calls = []

    async def scenario():
        timer = AsyncioTimer()

        async def first():
            calls.append("first")

        async def second():
            calls.append("second")

        timer.start(0, first)
        timer.start(0, second)
        await asyncio.sleep(0.01)

    asyncio.run(scenario())

    assert calls == ["second"]


def test_callback_can_cancel_its_own_timer():
    # VoiceSession.end() cancels the timer from inside the timer's callback
    calls = []

    async def scenario():
        timer = AsyncioTimer()

        async def callback():
            timer.cancel()
            await asyncio.sleep(0)
            calls.append("finished")

        timer.start(0, callback)
        await asyncio.sleep(0.01)

    asyncio.run(scenario())

    assert calls == ["finished"]
