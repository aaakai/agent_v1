from __future__ import annotations

import json

import pytest

from web_debug.api import run_debug_scenario


def test_run_debug_scenario_returns_simplified_summary_with_player() -> None:
    payload = run_debug_scenario("sfx", with_player=True)
    summary = payload["simplified_summary"]

    assert summary["headline"]
    assert "lanes" in summary
    assert "key_decisions" in summary
    assert "counters" in summary
    assert summary["narration"]
    assert summary["short_timeline"]
    assert "turn_summary" in summary
    assert summary["counters"]["player_command_count"] == len(payload["player_commands"])


def test_run_debug_scenario_returns_simplified_summary_without_player() -> None:
    payload = run_debug_scenario("sfx", with_player=False)
    summary = payload["simplified_summary"]

    assert payload["playback_state"] is None
    assert summary["lanes"]["speech"]["status"] == "idle"
    assert summary["counters"]["commands_applied"] == 0
    assert summary["narration"]


def test_run_debug_scenario_turn_final_returns_turn_summary() -> None:
    payload = run_debug_scenario("turn_final", with_player=True)
    summary = payload["simplified_summary"]

    assert summary["turn_summary"]["has_turn"] is True
    assert summary["turn_summary"]["last_flush_reason"] == "silence"
    assert summary["turn_summary"]["last_final_text"] == "我想测试一下"


def test_run_debug_scenario_unknown_still_raises_value_error() -> None:
    with pytest.raises(ValueError, match="available scenarios"):
        run_debug_scenario("nope", with_player=True)


def test_simplified_api_payload_is_json_serializable() -> None:
    payload = run_debug_scenario("backchannel", with_player=True)

    assert json.loads(json.dumps(payload, ensure_ascii=False))["simplified_summary"][
        "scenario"
    ] == "backchannel"
