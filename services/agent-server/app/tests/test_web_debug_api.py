from __future__ import annotations

import json

import pytest

from web_debug.api import list_scenarios, run_debug_scenario, validate_scenario_name


def test_list_scenarios_returns_expected_names() -> None:
    payload = list_scenarios()
    names = {item["name"] for item in payload["scenarios"]}

    assert payload["scenarios"]
    assert {"sfx", "full", "backchannel"}.issubset(names)
    assert all("description" in item for item in payload["scenarios"])


def test_run_debug_scenario_with_player_returns_playback_state() -> None:
    payload = run_debug_scenario("sfx", with_player=True)

    assert payload["scenario"] == "sfx"
    assert payload["with_player"] is True
    assert payload["debug_result"]["scenario"] == "sfx"
    assert payload["player_commands"]
    assert payload["playback_state"]["history"]
    assert payload["playback_state"]["sfx"]["active"]
    assert payload["commands_applied"] == len(payload["player_commands"])


def test_run_backchannel_with_player_returns_commands() -> None:
    payload = run_debug_scenario("backchannel", with_player=True)

    assert payload["player_commands"]
    assert payload["playback_state"]["history"]


def test_run_debug_scenario_without_player_returns_null_playback() -> None:
    payload = run_debug_scenario("sfx", with_player=False)

    assert payload["with_player"] is False
    assert payload["debug_result"]["scenario"] == "sfx"
    assert payload["playback_state"] is None
    assert payload["commands_applied"] == 0


def test_unknown_scenario_raises_with_available_options() -> None:
    with pytest.raises(ValueError, match="available scenarios"):
        validate_scenario_name("missing")


def test_run_debug_scenario_payload_is_json_serializable() -> None:
    payload = run_debug_scenario("full", with_player=True)

    assert json.loads(json.dumps(payload, ensure_ascii=False))["scenario"] == "full"
