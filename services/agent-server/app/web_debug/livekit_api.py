from __future__ import annotations

from typing import Any

from livekit import LiveKitConfig, LiveKitDebugState, LiveKitTokenRequest, create_token

DEFAULT_LIVEKIT_DEBUG_STATE = LiveKitDebugState()


def get_livekit_config_status() -> dict[str, Any]:
    config = LiveKitConfig.from_env()
    return {
        "configured": config.is_configured(),
        "missing_fields": config.missing_fields(),
        "safe_config": config.to_safe_dict(),
    }


def create_debug_token(
    payload: dict[str, Any],
    allow_mock: bool = False,
) -> dict[str, Any]:
    config = LiveKitConfig.from_env()
    room_name = str(payload.get("room_name") or config.default_room_name())
    identity = str(payload.get("identity") or "user-debug-1")
    request = LiveKitTokenRequest(
        room_name=room_name,
        identity=identity,
        name=payload.get("name"),
        can_publish=bool(payload.get("can_publish", True)),
        can_subscribe=bool(payload.get("can_subscribe", True)),
        ttl_seconds=int(payload.get("ttl_seconds", 3600)),
    )
    response = create_token(config=config, request=request, allow_mock=allow_mock)
    return response.model_dump(mode="python")


def get_debug_state() -> dict[str, Any]:
    return DEFAULT_LIVEKIT_DEBUG_STATE.snapshot()


def reset_debug_state() -> dict[str, Any]:
    DEFAULT_LIVEKIT_DEBUG_STATE.reset()
    return DEFAULT_LIVEKIT_DEBUG_STATE.snapshot()
