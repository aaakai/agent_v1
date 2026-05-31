from __future__ import annotations

from .config import LiveKitConfig
from .room_handler import LiveKitRoomHandler


def create_room_handler_from_env() -> LiveKitRoomHandler:
    return LiveKitRoomHandler(config=LiveKitConfig.from_env())


async def run_worker() -> None:
    handler = create_room_handler_from_env()
    if not handler.config.is_configured():
        missing = ", ".join(handler.config.missing_fields())
        raise ValueError(f"LiveKit config is incomplete: {missing}")
    raise NotImplementedError(
        "LiveKit worker connection is not implemented yet"
    )
