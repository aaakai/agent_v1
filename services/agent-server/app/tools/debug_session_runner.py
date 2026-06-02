from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from runtime.debug_session_runner import (  # noqa: E402
    DebugSessionRunner,
    result_to_json_dict,
)
from audio_runtime.mock_player import MockPlayerRuntime  # noqa: E402


def run(
    name: str,
    commands_only: bool = False,
    with_player: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    runner = DebugSessionRunner()
    scenario = runner.build_scenario(name)
    result = result_to_json_dict(runner.run_scenario_sync(scenario))
    if commands_only:
        return result["player_commands"]
    if with_player:
        player = MockPlayerRuntime(session_id=result["session_id"])
        updates = player.apply_commands(result["player_commands"])
        result["playback_state"] = player.snapshot()
        result["commands_applied"] = len(updates)
    return result


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    commands_only = "--commands-only" in args
    with_player = "--with-player" in args
    ignored = {"--commands-only", "--with-player"}
    positional = [arg for arg in args if arg not in ignored]
    name = positional[0] if positional else "backchannel"
    runner = DebugSessionRunner()
    if name not in runner.get_available_scenarios():
        options = ", ".join(runner.get_available_scenarios())
        print(f"unknown scenario: {name}", file=sys.stderr)
        print(f"available scenarios: {options}", file=sys.stderr)
        return 2

    scenario = runner.build_scenario(name)
    result = runner.run_scenario_sync(scenario)
    payload: Any = result_to_json_dict(result)
    if commands_only:
        payload = payload["player_commands"]
    elif with_player:
        player = MockPlayerRuntime(session_id=payload["session_id"])
        updates = player.apply_commands(payload["player_commands"])
        payload["playback_state"] = player.snapshot()
        payload["commands_applied"] = len(updates)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
