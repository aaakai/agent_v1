from __future__ import annotations

import pytest

from livekit import LiveKitConfig
from livekit.token import (
    LiveKitTokenRequest,
    create_dev_mock_token,
    create_token,
)


def test_create_dev_mock_token_returns_mock_response() -> None:
    config = LiveKitConfig(url="wss://example", api_key="key", api_secret="secret")
    request = LiveKitTokenRequest(room_name="room", identity="user")

    response = create_dev_mock_token(config, request)

    assert response.url == "wss://example"
    assert response.token == "mock-token-for-user-in-room"
    assert response.metadata["mock"] is True
    assert "secret" not in response.model_dump_json()


def test_create_token_allow_mock_does_not_require_sdk() -> None:
    config = LiveKitConfig(url="wss://example", api_key="key", api_secret="secret")
    request = LiveKitTokenRequest(room_name="room", identity="user")

    response = create_token(config, request, allow_mock=True)

    assert response.token
    assert response.room_name == "room"
    assert response.identity == "user"
    assert "secret" not in response.model_dump_json()


def test_create_token_rejects_incomplete_config() -> None:
    request = LiveKitTokenRequest(room_name="room", identity="user")

    with pytest.raises(ValueError, match="LiveKit config is incomplete"):
        create_token(LiveKitConfig(), request, allow_mock=True)
