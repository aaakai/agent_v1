from __future__ import annotations

import asyncio

from audio_input import AudioFrame, RawAudioRouter


def test_sync_consumer_receives_frame() -> None:
    router = RawAudioRouter()
    frame = AudioFrame(session_id="session-1")
    seen: list[AudioFrame] = []

    def consumer(received: AudioFrame) -> None:
        seen.append(received)

    router.add_consumer("sync", consumer)

    result = asyncio.run(router.route(frame))

    assert result["consumer_count"] == 1
    assert result["errors"] == []
    assert seen == [frame]


def test_async_consumer_receives_frame() -> None:
    router = RawAudioRouter()
    frame = AudioFrame(session_id="session-1")
    seen: list[AudioFrame] = []

    async def consumer(received: AudioFrame) -> None:
        await asyncio.sleep(0)
        seen.append(received)

    router.add_consumer("async", consumer)

    result = asyncio.run(router.route(frame))

    assert result["consumer_count"] == 1
    assert result["errors"] == []
    assert seen == [frame]


def test_multiple_consumers_receive_same_frame() -> None:
    router = RawAudioRouter()
    frame = AudioFrame(session_id="session-1")
    seen_a: list[str] = []
    seen_b: list[str] = []

    router.add_consumer("a", lambda received: seen_a.append(received.frame_id))
    router.add_consumer("b", lambda received: seen_b.append(received.frame_id))

    result = asyncio.run(router.route(frame))

    assert result["consumer_count"] == 2
    assert seen_a == [frame.frame_id]
    assert seen_b == [frame.frame_id]


def test_consumer_error_does_not_block_other_consumers() -> None:
    router = RawAudioRouter()
    frame = AudioFrame(session_id="session-1")
    seen: list[AudioFrame] = []

    def failing_consumer(received: AudioFrame) -> None:
        raise RuntimeError("boom")

    def good_consumer(received: AudioFrame) -> None:
        seen.append(received)

    router.add_consumer("bad", failing_consumer)
    router.add_consumer("good", good_consumer)

    result = asyncio.run(router.route(frame))

    assert seen == [frame]
    assert result["errors"] == [{"consumer": "bad", "error": "boom"}]


def test_ring_buffer_saves_routed_frame() -> None:
    router = RawAudioRouter()
    frame = AudioFrame(session_id="session-1")

    asyncio.run(router.route(frame))

    assert router.routed_count == 1
    assert router.get_recent_frames() == [frame]


def test_remove_consumer_stops_delivery() -> None:
    router = RawAudioRouter()
    frame = AudioFrame(session_id="session-1")
    seen: list[AudioFrame] = []

    router.add_consumer("sync", lambda received: seen.append(received))
    router.remove_consumer("sync")

    result = asyncio.run(router.route(frame))

    assert router.get_consumer_names() == []
    assert result["consumer_count"] == 0
    assert seen == []
