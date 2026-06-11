from __future__ import annotations

import pytest

from web_debug.livekit_api import (
    DEFAULT_LIVEKIT_DEBUG_STATE,
    get_worker_status,
    reset_worker_state,
)
from web_debug.server import FastAPI, create_app


def test_get_and_reset_worker_status(monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret-value")
    DEFAULT_LIVEKIT_DEBUG_STATE.mark_connected("room-1", "agent-1")

    status = get_worker_status()

    assert status["configured"] is True
    assert status["debug_state"]["connected"] is True
    assert status["safe_config"]["api_secret"] == "***"
    assert "secret-value" not in str(status)

    reset = reset_worker_state()
    assert reset["debug_state"]["connected"] is False


@pytest.mark.skipif(FastAPI is None, reason="FastAPI is not installed")
def test_livekit_worker_status_routes() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())

    status = client.get("/api/livekit/worker-status")
    reset = client.post("/api/livekit/worker-reset")

    assert status.status_code == 200
    assert reset.status_code == 200
    assert "debug_state" in status.json()
