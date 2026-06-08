from __future__ import annotations

from web_debug.livekit_api import (
    create_debug_token,
    get_debug_state,
    get_livekit_config_status,
    reset_debug_state,
)


def test_config_status_empty_env(monkeypatch) -> None:
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)

    status = get_livekit_config_status()

    assert status["configured"] is False
    assert status["missing_fields"] == ["url", "api_key", "api_secret"]
    assert status["safe_config"]["api_secret"] is None


def test_create_debug_token_allow_mock(monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")

    response = create_debug_token(
        {"room_name": "room", "identity": "user"},
        allow_mock=True,
    )

    assert response["token"]
    assert response["room_name"] == "room"
    assert response["identity"] == "user"
    assert "secret" not in str(response)


def test_get_and_reset_debug_state() -> None:
    reset_debug_state()

    state = get_debug_state()

    assert state["connected"] is False
    assert state["frames_received"] == 0
    assert reset_debug_state()["events"] == []
