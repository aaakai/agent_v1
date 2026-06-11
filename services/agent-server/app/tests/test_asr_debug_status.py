from __future__ import annotations

import pytest

from web_debug.livekit_api import get_asr_config_status, get_worker_status
from web_debug.server import FastAPI, create_app


def test_get_asr_config_status_masks_key(monkeypatch) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    status = get_asr_config_status()

    assert status["provider"] == "openai"
    assert status["configured"] is True
    assert status["safe_config"]["api_key"] == "***"
    assert "openai-secret" not in str(status)


def test_worker_status_includes_asr_config(monkeypatch) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "disabled")

    status = get_worker_status()

    assert status["asr_config"]["provider"] == "disabled"
    assert "debug_state" in status


@pytest.mark.skipif(FastAPI is None, reason="FastAPI is not installed")
def test_asr_config_route() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())

    response = client.get("/api/asr/config")

    assert response.status_code == 200
    assert "safe_config" in response.json()
