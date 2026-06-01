from __future__ import annotations

from audio_runtime import command_from_decision, commands_from_decisions


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
