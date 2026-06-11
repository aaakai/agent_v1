from __future__ import annotations

import asyncio

import pytest

from livekit import LiveKitAgentWorkerOptions
from livekit.worker import create_agent_worker_from_env, run_worker


def test_create_agent_worker_from_env(monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")
    monkeypatch.setenv("LIVEKIT_ROOM", "room-1")

    worker = create_agent_worker_from_env(
        LiveKitAgentWorkerOptions(room_name="room-override")
    )

    assert worker.config.is_configured() is True
    assert worker.options.room_name == "room-override"


def test_run_worker_rejects_incomplete_config(monkeypatch) -> None:
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)

    with pytest.raises(ValueError, match="LiveKit config is incomplete"):
        asyncio.run(run_worker(LiveKitAgentWorkerOptions(run_duration_seconds=0.01)))
