from __future__ import annotations

from .agent_worker import (
    LiveKitAgentWorker,
    LiveKitAgentWorkerOptions,
    LiveKitAgentWorkerResult,
)
from .config import LiveKitConfig
from .room_handler import LiveKitRoomHandler


def create_room_handler_from_env() -> LiveKitRoomHandler:
    return LiveKitRoomHandler(config=LiveKitConfig.from_env())


def create_agent_worker_from_env(
    options: LiveKitAgentWorkerOptions | None = None,
) -> LiveKitAgentWorker:
    return LiveKitAgentWorker(config=LiveKitConfig.from_env(), options=options)


async def run_worker(
    options: LiveKitAgentWorkerOptions | None = None,
) -> LiveKitAgentWorkerResult:
    worker = create_agent_worker_from_env(options)
    if not worker.config.is_configured():
        missing = ", ".join(worker.config.missing_fields())
        raise ValueError(f"LiveKit config is incomplete: {missing}")
    return await worker.connect_and_run()
