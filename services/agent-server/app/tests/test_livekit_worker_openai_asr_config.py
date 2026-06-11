from __future__ import annotations

from livekit import LiveKitAgentWorker, LiveKitAgentWorkerOptions, LiveKitConfig
from asr.openai_asr import OpenAIChunkedASRAdapter


def test_worker_openai_provider_uses_chunked_adapter(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    worker = LiveKitAgentWorker(
        config=LiveKitConfig(),
        options=LiveKitAgentWorkerOptions(
            asr_provider="openai",
            asr_model="gpt-4o-mini-transcribe",
            asr_chunk_duration_ms=1000,
        ),
    )

    assert isinstance(worker.asr_adapter, OpenAIChunkedASRAdapter)
    assert worker.asr_config.is_configured() is True
    assert worker.debug_state.snapshot()["asr"]["metadata"]["mode"] == "chunked_transcription"
    assert "openai-secret" not in str(worker.debug_state.snapshot())


def test_worker_openai_missing_key_status_configured_false(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ASR_API_KEY", raising=False)

    worker = LiveKitAgentWorker(
        config=LiveKitConfig(),
        options=LiveKitAgentWorkerOptions(asr_provider="openai"),
    )

    assert worker.asr_config.is_configured() is False
    assert worker.debug_state.snapshot()["asr"]["configured"] is False
