from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from audio_runtime.mock_player import MockPlayerHarness  # noqa: E402
from runtime.debug_session_runner import DebugSessionRunner  # noqa: E402


def run(
    scenario_name: str,
    state_only: bool = False,
    include_commands: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    harness = MockPlayerHarness()
    result = harness.run_debug_scenario_sync(scenario_name)
    if state_only:
        return result["playback_state"]
    if include_commands:
        return {
            "player_commands": result["player_commands"],
            "playback_state": result["playback_state"],
            "commands_applied": result["commands_applied"],
        }
    return result


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    state_only = "--state-only" in args
    include_commands = "--commands" in args
    pretty = "--no-pretty" not in args
    ignored = {"--state-only", "--commands", "--pretty", "--no-pretty"}
    positional = [arg for arg in args if arg not in ignored]
    scenario_name = positional[0] if positional else "full"

    runner = DebugSessionRunner()
    if scenario_name not in runner.get_available_scenarios():
        options = ", ".join(runner.get_available_scenarios())
        print(f"unknown scenario: {scenario_name}", file=sys.stderr)
        print(f"available scenarios: {options}", file=sys.stderr)
        return 2

    payload = run(
        scenario_name,
        state_only=state_only,
        include_commands=include_commands,
    )
    indent = 2 if pretty else None
    print(json.dumps(payload, ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
