from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from runtime import (  # noqa: E402
    run_simulation,
    simulate_backchannel_opportunity,
    simulate_dangerous_interrupt,
    simulate_normal_dialogue,
    simulate_sfx_trigger,
    simulate_user_barge_in,
)
from schemas import Event  # noqa: E402


SIMULATIONS: dict[str, Callable[[], list[Event]]] = {
    "normal": simulate_normal_dialogue,
    "backchannel": simulate_backchannel_opportunity,
    "bargein": simulate_user_barge_in,
    "danger": simulate_dangerous_interrupt,
    "sfx": simulate_sfx_trigger,
}


def run(name: str) -> dict[str, Any]:
    if name not in SIMULATIONS:
        raise ValueError(f"unknown simulation: {name}")
    return run_simulation(SIMULATIONS[name]())


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    name = args[0] if args else "normal"
    if name not in SIMULATIONS:
        options = ", ".join(sorted(SIMULATIONS))
        print(f"usage: simulate_user_turn.py [{options}]", file=sys.stderr)
        return 2
    print(json.dumps(run(name), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
