from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from audio_runtime.mock_player import MockPlayerHarness
from runtime.debug_session_runner import DebugSessionRunner, result_to_json_dict
from web_debug.summary import build_debug_summary


def list_scenarios() -> dict[str, list[dict[str, str]]]:
    runner = DebugSessionRunner()
    scenarios: list[dict[str, str]] = []
    for name in runner.get_available_scenarios():
        scenario = runner.build_scenario(name)
        scenarios.append(
            {
                "name": name,
                "description": scenario.description,
            }
        )
    return {"scenarios": scenarios}


def run_debug_scenario(scenario: str, with_player: bool = True) -> dict[str, Any]:
    validate_scenario_name(scenario)

    if with_player:
        result = MockPlayerHarness().run_debug_scenario_sync(scenario)
        response = {
            "scenario": scenario,
            "with_player": True,
            "debug_result": result["debug_result"],
            "player_commands": result["player_commands"],
            "playback_state": result["playback_state"],
            "commands_applied": result["commands_applied"],
        }
        response["simplified_summary"] = build_debug_summary(response)
        return json_response_dict(response)

    runner = DebugSessionRunner()
    debug_scenario = runner.build_scenario(scenario)
    debug_result = result_to_json_dict(runner.run_scenario_sync(debug_scenario))
    response = {
        "scenario": scenario,
        "with_player": False,
        "debug_result": debug_result,
        "player_commands": debug_result.get("player_commands", []),
        "playback_state": None,
        "commands_applied": 0,
    }
    response["simplified_summary"] = build_debug_summary(response)
    return json_response_dict(response)


def validate_scenario_name(scenario: str) -> None:
    runner = DebugSessionRunner()
    available = runner.get_available_scenarios()
    if scenario not in available:
        options = ", ".join(available)
        raise ValueError(f"unknown scenario: {scenario}; available scenarios: {options}")


def json_response_dict(data: Any) -> dict[str, Any]:
    normalized = _to_json_friendly(data)
    if not isinstance(normalized, dict):
        return {"data": normalized}
    return normalized


def _to_json_friendly(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _to_json_friendly(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_friendly(item) for item in value]
    if isinstance(value, tuple):
        return [_to_json_friendly(item) for item in value]

    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)
    return value
