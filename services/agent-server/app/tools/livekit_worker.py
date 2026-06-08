from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from livekit import LiveKitConfig, LiveKitRoomHandler  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Lulula LiveKit worker.")
    parser.add_argument("--room")
    parser.add_argument("--identity")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    config = LiveKitConfig.from_env()
    if args.room:
        config.room_name = args.room
    if args.identity:
        config.agent_identity = args.identity

    if args.dry_run:
        print(json.dumps(config.to_safe_dict(), ensure_ascii=False, indent=2))
        return 0

    if not config.is_configured():
        missing = ", ".join(config.missing_fields())
        print(f"LiveKit config is incomplete: {missing}", file=sys.stderr)
        return 2

    try:
        asyncio.run(LiveKitRoomHandler(config=config).start())
    except NotImplementedError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
