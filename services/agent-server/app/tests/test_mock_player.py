from __future__ import annotations

import json

from audio_runtime import PlayerCommand
from audio_runtime.mock_player import MockPlayerRuntime


def test_play_tts_updates_speech_current_and_queues_lower_priority() -> None:
    player = MockPlayerRuntime(session_id="s1")
    player.apply_command(
        PlayerCommand(
            session_id="s1",
            type="PLAY_TTS",
            payload={"text": "hello", "priority": 80},
        )
    )
    player.apply_command(
        PlayerCommand(
            session_id="s1",
            type="PLAY_TTS",
            payload={"text": "later", "priority": 20},
        )
    )

    snapshot = player.snapshot()
    assert snapshot["speech"]["current"]["payload"]["text"] == "hello"
    assert snapshot["speech"]["queue"][0]["payload"]["text"] == "later"


def test_play_backchannel_updates_speech_current() -> None:
    player = MockPlayerRuntime(session_id="s1")

    player.apply_command(
        PlayerCommand(
            session_id="s1",
            type="PLAY_BACKCHANNEL",
            payload={"text": "嗯"},
        )
    )

    current = player.snapshot()["speech"]["current"]
    assert current["type"] == "PLAY_BACKCHANNEL"
    assert current["kind"] == "backchannel"
    assert current["payload"]["text"] == "嗯"


def test_stop_tts_clears_speech_current_and_queue() -> None:
    player = MockPlayerRuntime(session_id="s1")
    player.apply_commands(
        [
            PlayerCommand(session_id="s1", type="PLAY_TTS", payload={"priority": 80}),
            PlayerCommand(session_id="s1", type="PLAY_TTS", payload={"priority": 20}),
            PlayerCommand(session_id="s1", type="STOP_TTS", payload={"reason": "barge"}),
        ]
    )

    speech = player.snapshot()["speech"]
    assert speech["current"] is None
    assert speech["queue"] == []
    assert speech["stopped"] is True


def test_play_and_stop_sfx_preserves_spatial() -> None:
    player = MockPlayerRuntime(session_id="s1")
    spatial = {"azimuth_deg": -30, "distance_m": 2.5}

    player.apply_command(
        PlayerCommand(
            session_id="s1",
            type="PLAY_SFX",
            payload={"event": "door_knock", "spatial": spatial},
        )
    )

    active = player.snapshot()["sfx"]["active"]
    assert active[0]["payload"]["spatial"] == spatial

    player.apply_command(
        PlayerCommand(
            session_id="s1",
            type="STOP_SFX",
            payload={"event": "door_knock"},
        )
    )

    snapshot = player.snapshot()
    assert snapshot["sfx"]["active"] == []
    assert snapshot["sfx"]["stopped"][0]["payload"]["event"] == "door_knock"


def test_set_ambience_and_duck_audio() -> None:
    player = MockPlayerRuntime(session_id="s1")

    player.apply_command(
        PlayerCommand(
            session_id="s1",
            type="SET_AMBIENCE",
            payload={"asset": "rain_alley_loop", "gain": 0.25},
        )
    )
    player.apply_command(PlayerCommand(session_id="s1", type="DUCK_AUDIO"))

    snapshot = player.snapshot()
    assert snapshot["ambience"]["current"]["payload"]["asset"] == "rain_alley_loop"
    assert snapshot["sfx"]["ducked"] is True
    assert snapshot["ambience"]["ducked"] is True


def test_unknown_command_does_not_raise_and_reset_clears_state() -> None:
    player = MockPlayerRuntime(session_id="s1")

    update = player.apply_command({"type": "NOPE", "payload": {}})

    assert update["applied"] is False
    assert update["reason"] == "unknown_command"
    assert player.snapshot()["command_count"] == 1

    player.reset()
    assert player.snapshot()["command_count"] == 0


def test_apply_commands_order_and_snapshot_json_serializable() -> None:
    player = MockPlayerRuntime(session_id="s1")

    updates = player.apply_commands(
        [
            PlayerCommand(session_id="s1", type="PLAY_SFX"),
            PlayerCommand(session_id="s1", type="SET_AMBIENCE"),
        ]
    )
    payload = player.snapshot()

    assert [update["type"] for update in updates] == ["PLAY_SFX", "SET_AMBIENCE"]
    assert json.loads(json.dumps(payload, ensure_ascii=False))["command_count"] == 2
