from __future__ import annotations

import json

from asr import ASRDiagnosticsStore, ASRProviderConfig, ASRProviderStatus, ASRResult
from audio_input import AudioFrame


def test_asr_diagnostics_records_frame_without_pcm() -> None:
    store = ASRDiagnosticsStore()
    frame = AudioFrame(session_id="s1", pcm=b"raw")

    store.record_frame(frame)
    snapshot = store.snapshot()

    assert snapshot["frames_sent"] == 1
    assert "pcm" not in str(snapshot)


def test_asr_diagnostics_records_result_and_error() -> None:
    store = ASRDiagnosticsStore()
    store.record_result(ASRResult(session_id="s1", text="hello", is_final=False, provider="mock"))
    store.record_result(ASRResult(session_id="s1", text="final hello", is_final=True, provider="mock"))
    store.record_error("bad", metadata={"provider": "mock"})
    store.record_flush("silence", results_count=1)

    snapshot = store.snapshot(
        status=ASRProviderStatus(provider="mock", configured=True),
        config=ASRProviderConfig(provider="mock"),
    )

    assert snapshot["recent_results"][0]["text"] == "hello"
    assert snapshot["errors"][0]["error"] == "bad"
    assert snapshot["flush_count"] == 1
    assert snapshot["last_flush_reason"] == "silence"
    assert snapshot["last_final_text"] == "final hello"
    json.dumps(snapshot)


def test_asr_diagnostics_reset() -> None:
    store = ASRDiagnosticsStore()
    store.record_error("bad")
    store.reset()

    assert store.snapshot()["errors"] == []
