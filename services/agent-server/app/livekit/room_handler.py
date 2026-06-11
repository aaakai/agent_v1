from __future__ import annotations

import asyncio
from typing import Any

from audio_input import RawAudioRouter
from runtime import RuntimeCoordinator
from schemas import Event
from schemas.event_types import USER_AUDIO_FRAME

from .audio_track_publisher import BaseAudioTrackPublisher
from .audio_track_reader import BaseAudioTrackReader
from .config import LiveKitConfig
from .debug_state import LiveKitDebugState


class LiveKitRoomHandler:
    def __init__(
        self,
        config: LiveKitConfig,
        raw_audio_router: RawAudioRouter | None = None,
        runtime_coordinator: RuntimeCoordinator | None = None,
        publisher: BaseAudioTrackPublisher | None = None,
        debug_state: LiveKitDebugState | None = None,
    ) -> None:
        self.config = config
        self.raw_audio_router = raw_audio_router or RawAudioRouter()
        self.runtime_coordinator = runtime_coordinator or RuntimeCoordinator()
        self.publisher = publisher
        self.debug_state = debug_state or LiveKitDebugState()
        self.active_reader_tasks: dict[str, asyncio.Task[dict[str, Any]]] = {}
        self.frames_processed_total = 0

    async def handle_audio_reader(
        self,
        reader: BaseAudioTrackReader,
    ) -> dict[str, Any]:
        frames_processed = 0
        errors: list[dict[str, Any]] = []

        try:
            async for frame in reader.read_frames():
                route_result = await self.raw_audio_router.route(frame)
                errors.extend(route_result["errors"])
                frames_processed += 1
                self.debug_state.mark_frame_received(
                    frame.timestamp_ms,
                    metadata={
                        "frame_id": frame.frame_id,
                        "duration_ms": frame.duration_ms,
                        "sample_rate": frame.sample_rate,
                        "channels": frame.channels,
                    },
                )
                self.runtime_coordinator.process_event(
                    Event(
                        session_id=frame.session_id,
                        type=USER_AUDIO_FRAME,
                        timestamp_ms=frame.timestamp_ms,
                        source=frame.source,
                        payload={
                            "frame_id": frame.frame_id,
                            "timestamp_ms": frame.timestamp_ms,
                            "sample_rate": frame.sample_rate,
                            "channels": frame.channels,
                            "duration_ms": frame.duration_ms,
                        },
                    )
                )
        except Exception as exc:  # noqa: BLE001 - reader errors are debug data.
            error = {"error": str(exc)}
            errors.append(error)
            self.debug_state.append_event(
                "reader_error",
                str(exc),
                metadata=error,
            )

        self.frames_processed_total += frames_processed
        return {
            "frames_processed": frames_processed,
            "errors": errors,
        }

    def start_reader_task(
        self,
        reader: BaseAudioTrackReader,
        track_id: str | None = None,
    ) -> asyncio.Task[dict[str, Any]]:
        task_id = track_id or str(id(reader))
        task = asyncio.create_task(self.handle_audio_reader(reader))
        self.active_reader_tasks[task_id] = task

        def cleanup(_task: asyncio.Task[dict[str, Any]]) -> None:
            self.active_reader_tasks.pop(task_id, None)

        task.add_done_callback(cleanup)
        return task

    async def stop_all_reader_tasks(self) -> None:
        tasks = list(self.active_reader_tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.active_reader_tasks.clear()

    async def start(self) -> None:
        if not self.config.is_configured():
            missing = ", ".join(self.config.missing_fields())
            raise ValueError(f"LiveKit config is incomplete: {missing}")
        raise NotImplementedError(
            "LiveKit worker connection is not implemented yet"
        )
