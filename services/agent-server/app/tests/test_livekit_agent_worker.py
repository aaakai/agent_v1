from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from audio_input import AudioFrame, RawAudioRouter
from livekit import (
    LiveKitAgentWorker,
    LiveKitAgentWorkerOptions,
    LiveKitConfig,
    LiveKitDebugState,
    MockAudioTrackReader,
)
from runtime import RuntimeCoordinator


def configured_config() -> LiveKitConfig:
    return LiveKitConfig(
        url="wss://example.livekit.cloud",
        api_key="key",
        api_secret="secret",
        room_name="room-1",
    )


def test_agent_worker_default_initialization() -> None:
    worker = LiveKitAgentWorker(config=LiveKitConfig(), options=LiveKitAgentWorkerOptions())

    assert isinstance(worker.raw_audio_router, RawAudioRouter)
    assert isinstance(worker.runtime_coordinator, RuntimeCoordinator)
    assert isinstance(worker.debug_state, LiveKitDebugState)
    assert set(worker.raw_audio_router.get_consumer_names()) == {
        "asr",
        "asr_flush",
        "backchannel",
    }


def test_agent_worker_audio_track_detection() -> None:
    worker = LiveKitAgentWorker(config=LiveKitConfig())

    assert worker._is_audio_track(SimpleNamespace(kind="audio"), None) is True
    assert worker._is_audio_track(SimpleNamespace(kind="KIND_AUDIO"), None) is True
    assert worker._is_audio_track(SimpleNamespace(kind="video"), None) is False
    assert worker._is_audio_track(SimpleNamespace(), SimpleNamespace(source="microphone")) is True


def test_agent_worker_identity_and_track_sid_helpers() -> None:
    worker = LiveKitAgentWorker(config=LiveKitConfig())

    assert worker._participant_identity(SimpleNamespace(identity="user-1")) == "user-1"
    assert worker._participant_identity(SimpleNamespace(sid="participant-sid")) == "participant-sid"
    assert worker._track_sid(SimpleNamespace(sid="pub-sid"), SimpleNamespace(sid="track-sid")) == "pub-sid"
    assert worker._track_sid(None, SimpleNamespace(sid="track-sid")) == "track-sid"


def test_handle_track_subscribed_audio_routes_reader_and_updates_debug_state() -> None:
    frame = AudioFrame(session_id="user-1", frame_id="frame-1")
    debug_state = LiveKitDebugState()
    router = RawAudioRouter()
    seen: list[str] = []
    router.add_consumer("seen", lambda received: seen.append(received.frame_id))
    worker = LiveKitAgentWorker(
        config=configured_config(),
        options=LiveKitAgentWorkerOptions(enable_runtime_consumers=False),
        raw_audio_router=router,
        debug_state=debug_state,
    )

    def reader_factory(**_: object) -> MockAudioTrackReader:
        return MockAudioTrackReader([frame])

    worker.audio_track_reader_cls = reader_factory

    asyncio.run(
        worker._handle_track_subscribed(
            SimpleNamespace(kind="audio", sid="track-1"),
            SimpleNamespace(sid="pub-1", source="microphone"),
            SimpleNamespace(identity="user-1"),
        )
    )

    assert seen == ["frame-1"]
    assert worker.tracks_subscribed == 1
    assert debug_state.frames_received == 1
    assert "pub-1" in debug_state.tracks


def test_handle_track_subscribed_ignores_video_track() -> None:
    worker = LiveKitAgentWorker(
        config=configured_config(),
        options=LiveKitAgentWorkerOptions(enable_runtime_consumers=False),
    )
    calls = 0

    def reader_factory(**_: object) -> MockAudioTrackReader:
        nonlocal calls
        calls += 1
        return MockAudioTrackReader([])

    worker.audio_track_reader_cls = reader_factory

    asyncio.run(
        worker._handle_track_subscribed(
            SimpleNamespace(kind="video", sid="track-1"),
            SimpleNamespace(sid="pub-1"),
            SimpleNamespace(identity="user-1"),
        )
    )

    assert calls == 0
    assert worker.debug_state.events[-1].type == "track_ignored"


def test_connect_and_run_rejects_incomplete_config() -> None:
    worker = LiveKitAgentWorker(config=LiveKitConfig())

    with pytest.raises(ValueError, match="LiveKit config is incomplete"):
        asyncio.run(worker.connect_and_run())
