from __future__ import annotations

import asyncio

from asr import ASRResult, MockASRAdapter
from audio_input import AudioFrame


def test_scripted_results_are_returned_in_order_and_session_is_fixed() -> None:
    adapter = MockASRAdapter(
        scripted_results=[
            {"session_id": "other", "text": "first", "is_final": False},
            ASRResult(session_id="session-1", text="second", is_final=True),
        ]
    )
    frame = AudioFrame(session_id="session-1", timestamp_ms=100)

    async def run() -> list[ASRResult]:
        first = await adapter.send_audio(frame)
        second = await adapter.send_audio(frame)
        return [*first, *second]

    results = asyncio.run(run())

    assert [result.text for result in results] == ["first", "second"]
    assert all(result.session_id == "session-1" for result in results)
    assert results[0].timestamp_ms == 100


def test_frame_metadata_asr_text_generates_partial() -> None:
    adapter = MockASRAdapter()
    frame = AudioFrame(
        session_id="session-1",
        timestamp_ms=123,
        metadata={"asr_text": "partial text"},
    )

    results = asyncio.run(adapter.send_audio(frame))

    assert len(results) == 1
    assert results[0].text == "partial text"
    assert results[0].is_final is False
    assert results[0].stability == 0.7
    assert results[0].timestamp_ms == 123


def test_frame_metadata_asr_final_generates_final_result() -> None:
    adapter = MockASRAdapter()
    frame = AudioFrame(
        session_id="session-1",
        metadata={
            "asr_text": "final text",
            "asr_final": True,
            "asr_metadata": {"source": "unit-test"},
        },
    )

    results = asyncio.run(adapter.send_audio(frame))

    assert results[0].text == "final text"
    assert results[0].is_final is True
    assert results[0].stability == 1.0
    assert results[0].metadata == {"source": "unit-test"}


def test_start_stream_and_close_update_adapter_state() -> None:
    adapter = MockASRAdapter()

    async def run() -> None:
        await adapter.start_stream("session-1")
        await adapter.close()

    asyncio.run(run())

    assert adapter.started_sessions == {"session-1"}
    assert adapter.closed is True
