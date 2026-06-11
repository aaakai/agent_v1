from __future__ import annotations

import json

from livekit import LiveKitDebugState


def test_debug_state_records_connection_frames_and_reset() -> None:
    state = LiveKitDebugState(max_events=3)

    state.mark_connected("room", "agent")
    state.mark_participant_joined("user")
    state.mark_track_subscribed("track-1", "user")
    state.mark_frame_received(1234, metadata={"frame_id": "frame-1"})

    snapshot = state.snapshot()
    assert snapshot["connected"] is True
    assert snapshot["frames_received"] == 1
    assert snapshot["last_frame_timestamp_ms"] == 1234
    assert snapshot["events"][-1]["type"] == "frame_received"
    assert len(snapshot["events"]) == 3
    assert json.loads(json.dumps(snapshot))["room_name"] == "room"

    state.reset()
    assert state.snapshot()["frames_received"] == 0
    assert state.snapshot()["events"] == []


def test_debug_state_records_asr_status_and_error_without_secret() -> None:
    state = LiveKitDebugState()

    state.update_asr_status({"provider": "mock", "api_key": "secret-value"})
    state.record_asr_error("asr failed", metadata={"api_secret": "secret-value"})

    snapshot = state.snapshot()
    assert snapshot["asr"]["provider"] == "mock"
    assert snapshot["asr"]["api_key"] == "***"
    assert snapshot["asr"]["last_error"] == "asr failed"
    assert "secret-value" not in str(snapshot)
