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


def run(name: str) -> dict[str, Any]:
    runner = DebugSessionRunner()
    scenario = runner.build_scenario(name)
    return result_to_json_dict(runner.run_scenario_sync(scenario))


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    name = args[0] if args else "backchannel"
    runner = DebugSessionRunner()
    if name not in runner.get_available_scenarios():
        options = ", ".join(runner.get_available_scenarios())
        print(f"unknown scenario: {name}", file=sys.stderr)
        print(f"available scenarios: {options}", file=sys.stderr)
        return 2

    scenario = runner.build_scenario(name)
    result = runner.run_scenario_sync(scenario)
    print(json.dumps(result_to_json_dict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
