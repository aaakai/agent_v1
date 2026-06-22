from __future__ import annotations

from livekit import LiveKitAgentWorker, LiveKitAgentWorkerOptions, LiveKitConfig
from web_debug.livekit_api import get_worker_status


def test_worker_debug_state_contains_asr_flush_info() -> None:
    worker = LiveKitAgentWorker(
        config=LiveKitConfig(),
        options=LiveKitAgentWorkerOptions(asr_silence_flush_ms=800),
    )

    asr = worker.debug_state.snapshot()["asr"]

    assert asr["flush_trigger"]["turn_detector"]["silence_flush_ms"] == 800
    assert asr["trigger"]["diagnostics"]["flush_count"] == 0


def test_web_worker_status_contains_asr_config() -> None:
    status = get_worker_status()

    assert "asr_config" in status
    assert "debug_state" in status
