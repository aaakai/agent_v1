from __future__ import annotations

import json

from audio_runtime import PlaybackState


def test_playback_state_defaults_and_snapshot_are_json_friendly() -> None:
    state = PlaybackState(session_id="s1")

    snapshot = state.snapshot()

    assert snapshot["session_id"] == "s1"
    assert snapshot["speech"]["current"] is None
    assert snapshot["sfx"]["active"] == []
    assert snapshot["ambience"]["current"] is None
    assert json.loads(json.dumps(snapshot, ensure_ascii=False))["session_id"] == "s1"


def test_playback_state_append_history_and_reset() -> None:
    state = PlaybackState(session_id="s1")
    state.speech.current = {"type": "PLAY_TTS"}
    state.sfx.active.append({"type": "PLAY_SFX"})
    state.command_count = 2

    state.append_history({"type": "PLAY_TTS"})

    assert state.history == [{"type": "PLAY_TTS"}]

    state.reset()

    assert state.session_id == "s1"
    assert state.command_count == 0
    assert state.history == []
    assert state.speech.current is None
    assert state.sfx.active == []
