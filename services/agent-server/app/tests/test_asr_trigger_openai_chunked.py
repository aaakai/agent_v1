from __future__ import annotations

import asyncio

from asr import ASRProviderConfig, ASRTrigger, BaseASRAdapter
from asr.openai_asr import OpenAIChunkedASRAdapter
from audio_input import AudioFrame
from runtime import RuntimeCoordinator


class FakeTranscriptions:
    def create(self, **kwargs):
        return {"text": "最终文本"}


class FakeClient:
    def __init__(self) -> None:
        self.audio = type("Audio", (), {"transcriptions": FakeTranscriptions()})()


def test_asr_trigger_flush_updates_final_state() -> None:
    coordinator = RuntimeCoordinator()
    adapter = OpenAIChunkedASRAdapter(
        ASRProviderConfig(
            provider="openai",
            api_key="key",
            model="gpt-4o-mini-transcribe",
            chunk_duration_ms=1000,
            min_chunk_duration_ms=50,
        ),
        client=FakeClient(),
    )
    trigger = ASRTrigger("s1", coordinator, adapter)

    async def run():
        await trigger.start()
        await adapter.send_audio(
            AudioFrame(
                session_id="s1",
                samples_per_channel=1600,
                pcm=b"\x01\x00" * 1600,
            )
        )
        return await trigger.flush()

    decisions = asyncio.run(run())

    assert decisions
    assert coordinator.get_session_state("s1").asr.final == "最终文本"


class BrokenFlushAdapter(BaseASRAdapter):
    async def flush(self):
        raise RuntimeError("flush failed")


def test_asr_trigger_flush_error_recorded() -> None:
    trigger = ASRTrigger("s1", RuntimeCoordinator(), BrokenFlushAdapter())

    result = asyncio.run(trigger.flush())

    assert result[0]["type"] == "asr_error"
    assert trigger.get_status()["diagnostics"]["errors"][0]["error"] == "flush failed"
