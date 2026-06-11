from __future__ import annotations

from web_debug.livekit_api import get_asr_config_status


def test_openai_asr_config_status_is_safe(monkeypatch) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("ASR_CHUNK_DURATION_MS", "1000")

    status = get_asr_config_status()

    assert status["provider"] == "openai"
    assert status["configured"] is True
    assert status["safe_config"]["chunk_duration_ms"] == 1000
    assert status["safe_config"]["api_key"] == "***"
    assert "openai-secret" not in str(status)
