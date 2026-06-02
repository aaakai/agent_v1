from __future__ import annotations

import json

from runtime.debug_session_runner import DebugSessionRunner, result_to_json_dict


def test_debug_sfx_scenario_records_play_sfx_command() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("sfx"))

    assert any(command["type"] == "PLAY_SFX" for command in result.player_commands)


def test_debug_backchannel_scenario_records_speech_command() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("backchannel"))

    assert result.player_commands
    assert any(
        command["type"] in {"PLAY_BACKCHANNEL", "PLAY_TTS"}
        for command in result.player_commands
    )


def test_debug_ambience_scenario_records_set_ambience_command() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("ambience"))

    assert any(
        command["type"] == "SET_AMBIENCE" for command in result.player_commands
    )


def test_debug_full_scenario_player_commands_are_json_serializable() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("full"))
    payload = result_to_json_dict(result)

    assert isinstance(payload["player_commands"], list)
    assert json.loads(json.dumps(payload, ensure_ascii=False))["scenario"] == "full"
