from __future__ import annotations

import json

from audio_runtime import command_from_decision, commands_from_decisions
from audio_runtime.player_protocol import command_to_dict, commands_to_dict


def test_sfx_play_decision_maps_to_play_sfx() -> None:
    command = command_from_decision(
        {"session_id": "s1", "decision": "play", "lane": "sfx"}
    )

    assert command.type == "PLAY_SFX"
    assert command.session_id == "s1"
    assert command.command_id
    assert command.timestamp_ms > 0


def test_ambience_play_or_replace_maps_to_set_ambience() -> None:
    play = command_from_decision(
        {"session_id": "s1", "decision": "play", "lane": "ambience"}
    )
    replace = command_from_decision(
        {"session_id": "s1", "decision": "replace", "lane": "ambience"}
    )

    assert play.type == "SET_AMBIENCE"
    assert replace.type == "SET_AMBIENCE"


def test_speech_stop_maps_to_stop_tts() -> None:
    command = command_from_decision(
        {"session_id": "s1", "decision": "stop", "lane": "speech"}
    )

    assert command.type == "STOP_TTS"


def test_speech_play_maps_to_backchannel_or_tts() -> None:
    backchannel = command_from_decision(
        {
            "session_id": "s1",
            "decision": "play",
            "lane": "speech",
            "proposal_action": "BACKCHANNEL",
        }
    )
    tts = command_from_decision(
        {
            "session_id": "s1",
            "decision": "play",
            "lane": "speech",
            "proposal_action": "SPEAK",
        }
    )

    assert backchannel.type == "PLAY_BACKCHANNEL"
    assert tts.type == "PLAY_TTS"


def test_duck_maps_to_duck_audio() -> None:
    command = command_from_decision(
        {"session_id": "s1", "decision": "duck", "lane": "sfx"}
    )

    assert command.type == "DUCK_AUDIO"


def test_unknown_decision_returns_none_and_batch_filters() -> None:
    commands = commands_from_decisions(
        [
            {"session_id": "s1", "decision": "unknown", "lane": "sfx"},
            {"session_id": "s1", "decision": "play", "lane": "sfx"},
        ]
    )

    assert command_from_decision({"decision": "unknown"}) is None
    assert [command.type for command in commands] == ["PLAY_SFX"]


def test_player_command_serialization_helpers_are_json_friendly() -> None:
    command = command_from_decision(
        {
            "session_id": "s1",
            "decision": "play",
            "lane": "speech",
            "proposal": {"action": "BACKCHANNEL"},
            "text": "嗯",
        }
    )

    payload = command_to_dict(command)
    batch = commands_to_dict([command])

    assert payload["type"] == "PLAY_BACKCHANNEL"
    assert batch[0]["payload"]["text"] == "嗯"
    assert json.loads(json.dumps(batch, ensure_ascii=False))[0]["type"] == "PLAY_BACKCHANNEL"


def test_player_command_payload_keeps_proposal_metadata_for_player() -> None:
    command = command_from_decision(
        {
            "session_id": "s1",
            "decision": "play",
            "lane": "sfx",
            "proposal": {
                "action": "PLAY_SFX",
                "agent": "sfx_planner",
                "priority": 20,
                "metadata": {
                    "event": "door_knock",
                    "spatial": {"azimuth_deg": -30},
                },
                "mixing": {"gain": 0.55},
            },
        }
    )

    assert command.type == "PLAY_SFX"
    assert command.payload["event"] == "door_knock"
    assert command.payload["spatial"]["azimuth_deg"] == -30
    assert command.payload["gain"] == 0.55
    assert command.payload["original_decision"]["lane"] == "sfx"


def test_ambience_and_speech_payloads_are_player_friendly() -> None:
    ambience = command_from_decision(
        {
            "session_id": "s1",
            "decision": "replace",
            "lane": "ambience",
            "proposal": {
                "action": "SET_AMBIENCE",
                "metadata": {"scene": "rainy_alley", "asset": "rain_alley_loop"},
                "mixing": {"gain": 0.25, "loop": True, "fade_ms": 1200},
            },
        }
    )
    speech = command_from_decision(
        {
            "session_id": "s1",
            "decision": "play",
            "lane": "speech",
            "proposal_action": "SPEAK",
            "proposal": {
                "action": "SPEAK",
                "agent": "dialogue",
                "text": "hello",
                "priority": 50,
            },
        }
    )

    assert ambience.type == "SET_AMBIENCE"
    assert ambience.payload["asset"] == "rain_alley_loop"
    assert ambience.payload["gain"] == 0.25
    assert speech.type == "PLAY_TTS"
    assert speech.payload["text"] == "hello"
    assert speech.payload["agent"] == "dialogue"
