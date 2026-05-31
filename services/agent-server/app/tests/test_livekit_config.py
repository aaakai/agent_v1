from __future__ import annotations

from livekit import LiveKitConfig


def test_config_from_empty_env_is_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
    monkeypatch.delenv("LIVEKIT_ROOM", raising=False)
    monkeypatch.delenv("LIVEKIT_AGENT_IDENTITY", raising=False)

    config = LiveKitConfig.from_env()

    assert config.is_configured() is False
    assert config.missing_fields() == ["url", "api_key", "api_secret"]
    assert config.agent_identity == "lulula-agent"


def test_config_from_env_reads_complete_config(monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")
    monkeypatch.setenv("LIVEKIT_ROOM", "room-1")
    monkeypatch.setenv("LIVEKIT_AGENT_IDENTITY", "agent-1")

    config = LiveKitConfig.from_env()

    assert config.is_configured() is True
    assert config.missing_fields() == []
    assert config.url == "wss://example.livekit.cloud"
    assert config.api_key == "key"
    assert config.api_secret == "secret"
    assert config.room_name == "room-1"
    assert config.agent_identity == "agent-1"
