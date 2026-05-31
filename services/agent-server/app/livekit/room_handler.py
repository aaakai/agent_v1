from __future__ import annotations

from typing import Any

from audio_input import RawAudioRouter
from runtime import RuntimeCoordinator
from schemas import Event
from schemas.event_types import USER_AUDIO_FRAME

from .audio_track_publisher import BaseAudioTrackPublisher
from .audio_track_reader import BaseAudioTrackReader
from .config import LiveKitConfig


class LiveKitRoomHandler:
    def __init__(
        self,
        config: LiveKitConfig,
        raw_audio_router: RawAudioRouter | None = None,
        runtime_coordinator: RuntimeCoordinator | None = None,
        publisher: BaseAudioTrackPublisher | None = None,
    ) -> None:
        self.config = config
        self.raw_audio_router = raw_audio_router or RawAudioRouter()
        self.runtime_coordinator = runtime_coordinator or RuntimeCoordinator()
        self.publisher = publisher

    async def handle_audio_reader(
        self,
        reader: BaseAudioTrackReader,
    ) -> dict[str, Any]:
        frames_processed = 0
        errors: list[dict[str, Any]] = []

        async for frame in reader.read_frames():
            route_result = await self.raw_audio_router.route(frame)
            errors.extend(route_result["errors"])
            frames_processed += 1
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

        return {
            "frames_processed": frames_processed,
            "errors": errors,
        }

    async def start(self) -> None:
        if not self.config.is_configured():
            missing = ", ".join(self.config.missing_fields())
            raise ValueError(f"LiveKit config is incomplete: {missing}")
        raise NotImplementedError(
            "LiveKit worker connection is not implemented yet"
        )
