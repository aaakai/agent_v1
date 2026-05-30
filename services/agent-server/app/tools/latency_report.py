from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from runtime import (  # noqa: E402
    calculate_decision_latencies,
    load_jsonl_events,
    replay_events,
    summarize_latencies,
)


def run(path: str | Path) -> dict[str, Any]:
    events = load_jsonl_events(path)
    replay_result = replay_events(events)
    latencies = calculate_decision_latencies(events, replay_result["decisions"])
    return {
        "latencies": latencies,
        "summary": summarize_latencies(latencies),
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: latency_report.py <jsonl_path>", file=sys.stderr)
        return 2
    print(json.dumps(run(args[0]), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
