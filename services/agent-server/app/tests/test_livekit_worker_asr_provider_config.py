from __future__ import annotations

from livekit import LiveKitAgentWorker, LiveKitAgentWorkerOptions, LiveKitConfig


def test_livekit_worker_defaults_to_mock_asr(monkeypatch) -> None:
    monkeypatch.delenv("ASR_PROVIDER", raising=False)
    worker = LiveKitAgentWorker(config=LiveKitConfig())

    assert "asr" in worker.raw_audio_router.get_consumer_names()
    assert "asr_flush" in worker.raw_audio_router.get_consumer_names()
    assert worker.asr_config.normalized_provider() == "mock"
    assert worker.debug_state.snapshot()["asr"]["provider"] == "mock"


def test_livekit_worker_can_disable_asr() -> None:
    worker = LiveKitAgentWorker(
        config=LiveKitConfig(),
        options=LiveKitAgentWorkerOptions(asr_enabled=False),
    )

    assert worker.asr_config.normalized_provider() == "disabled"
    assert worker.asr_adapter.get_status().provider == "disabled"


def test_livekit_worker_asr_provider_option_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "deepgram")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "deep-secret")

    worker = LiveKitAgentWorker(
        config=LiveKitConfig(),
        options=LiveKitAgentWorkerOptions(asr_provider="mock"),
    )

    assert worker.asr_config.normalized_provider() == "mock"
    assert "deep-secret" not in str(worker.debug_state.snapshot())


def test_livekit_worker_reads_deepgram_env_without_leaking_secret(monkeypatch) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "deepgram")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "deep-secret")

    worker = LiveKitAgentWorker(config=LiveKitConfig())
    snapshot = worker.debug_state.snapshot()

    assert snapshot["asr"]["provider"] == "deepgram"
    assert snapshot["asr"]["configured"] is True
    assert "deep-secret" not in str(snapshot)


def test_livekit_worker_asr_flush_options_and_disable() -> None:
    worker = LiveKitAgentWorker(
        config=LiveKitConfig(),
        options=LiveKitAgentWorkerOptions(
            asr_silence_flush_ms=900,
            asr_min_speech_ms=100,
            asr_max_turn_ms=5000,
        ),
    )

    status = worker.debug_state.snapshot()["asr"]["flush_trigger"]
    assert status["turn_detector"]["silence_flush_ms"] == 900
    assert status["turn_detector"]["min_speech_ms"] == 100
    assert status["turn_detector"]["max_turn_ms"] == 5000

    disabled = LiveKitAgentWorker(
        config=LiveKitConfig(),
        options=LiveKitAgentWorkerOptions(asr_flush_on_silence=False),
    )
    assert "asr_flush" not in disabled.raw_audio_router.get_consumer_names()
