from __future__ import annotations

import asyncio

from asr import ASRResult, MockStreamingASRAdapter
from audio_input import AudioFrame


def test_mock_streaming_scripted_results() -> None:
    adapter = MockStreamingASRAdapter(
        scripted_results=[
            {"session_id": "s1", "text": "part", "is_final": False},
            ASRResult(session_id="s1", text="done", is_final=True),
        ]
    )

    async def run():
        await adapter.start_stream("s1")
        first = await adapter.send_audio(AudioFrame(session_id="s1"))
        second = await adapter.send_audio(AudioFrame(session_id="s1"))
        return first, second

    first, second = asyncio.run(run())

    assert first[0].text == "part"
    assert second[0].is_final is True
    assert adapter.get_status().results_emitted == 2


def test_mock_streaming_metadata_asr_text_partial_and_final() -> None:
    adapter = MockStreamingASRAdapter()

    async def run():
        await adapter.start_stream("s1")
        partial = await adapter.send_audio(AudioFrame(session_id="s1", metadata={"asr_text": "hi"}))
        final = await adapter.send_audio(
            AudioFrame(session_id="s1", metadata={"asr_text": "done", "asr_final": True})
        )
        return partial, final

    partial, final = asyncio.run(run())

    assert partial[0].is_final is False
    assert final[0].is_final is True


def test_mock_streaming_default_text_final_after_frames() -> None:
    adapter = MockStreamingASRAdapter(default_text="hello", final_after_frames=2)

    async def run():
        await adapter.start_stream("s1")
        first = await adapter.send_audio(AudioFrame(session_id="s1"))
        second = await adapter.send_audio(AudioFrame(session_id="s1"))
        return first, second

    first, second = asyncio.run(run())

    assert first[0].is_final is False
    assert second[0].is_final is True
    assert adapter.get_status().finals_emitted == 1


def test_mock_streaming_close_sets_closed() -> None:
    adapter = MockStreamingASRAdapter()

    asyncio.run(adapter.close())

    assert adapter.closed is True
