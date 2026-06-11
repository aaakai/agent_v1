from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from asr import ASRProviderConfig  # noqa: E402
from livekit import LiveKitAgentWorkerOptions, LiveKitConfig  # noqa: E402
from livekit.worker import run_worker  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Lulula LiveKit worker.")
    parser.add_argument("--room")
    parser.add_argument("--identity")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--duration", type=float)
    parser.add_argument("--no-runtime-consumers", action="store_true")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--asr-provider")
    parser.add_argument("--asr-language")
    parser.add_argument("--asr-model")
    parser.add_argument("--disable-asr", action="store_true")
    parser.add_argument("--asr-chunk-ms", type=int)
    parser.add_argument("--asr-min-chunk-ms", type=int)
    parser.add_argument("--asr-max-buffer-ms", type=int)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    config = LiveKitConfig.from_env()
    if args.room:
        config.room_name = args.room
    if args.identity:
        config.agent_identity = args.identity

    options = LiveKitAgentWorkerOptions(
        room_name=config.default_room_name(),
        agent_identity=config.agent_identity,
        run_duration_seconds=args.duration,
        enable_runtime_consumers=not args.no_runtime_consumers,
        sample_rate=args.sample_rate,
        channels=args.channels,
        asr_provider=args.asr_provider,
        asr_language=args.asr_language,
        asr_model=args.asr_model,
        asr_enabled=not args.disable_asr,
        asr_chunk_duration_ms=args.asr_chunk_ms,
        asr_min_chunk_duration_ms=args.asr_min_chunk_ms,
        asr_max_buffer_duration_ms=args.asr_max_buffer_ms,
    )
    asr_config = ASRProviderConfig.from_env()
    asr_updates = {
        "sample_rate": args.sample_rate,
        "channels": args.channels,
    }
    if args.disable_asr:
        asr_updates["provider"] = "disabled"
    elif args.asr_provider:
        asr_updates["provider"] = args.asr_provider
    if args.asr_language:
        asr_updates["language"] = args.asr_language
    if args.asr_model:
        asr_updates["model"] = args.asr_model
    if args.asr_chunk_ms is not None:
        asr_updates["chunk_duration_ms"] = args.asr_chunk_ms
    if args.asr_min_chunk_ms is not None:
        asr_updates["min_chunk_duration_ms"] = args.asr_min_chunk_ms
    if args.asr_max_buffer_ms is not None:
        asr_updates["max_buffer_duration_ms"] = args.asr_max_buffer_ms
    asr_config = asr_config.model_copy(update=asr_updates).with_env_credentials()

    if args.dry_run:
        print(
            json.dumps(
                {
                    "safe_config": config.to_safe_dict(),
                    "safe_asr_config": asr_config.to_safe_dict(),
                    "worker_options": options.model_dump(mode="python"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not config.is_configured():
        missing = ", ".join(config.missing_fields())
        print(f"LiveKit config is incomplete: {missing}", file=sys.stderr)
        return 2

    try:
        result = asyncio.run(run_worker(options))
    except (RuntimeError, NotImplementedError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(json.dumps(result.model_dump(mode="python"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
