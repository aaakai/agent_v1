from __future__ import annotations

from typing import Any

from runtime import RuntimeCoordinator

from .audio_frame import AudioFrame
from .feature_extractor import AudioFeatureExtractor


class BackchannelTrigger:
    def __init__(
        self,
        session_id: str,
        runtime_coordinator: RuntimeCoordinator,
        extractor: AudioFeatureExtractor | None = None,
    ) -> None:
        self.session_id = session_id
        self.runtime_coordinator = runtime_coordinator
        self.extractor = extractor or AudioFeatureExtractor()

    async def consume(self, frame: AudioFrame) -> list[dict[str, Any]]:
        features = self.extractor.extract(frame)
        session_id = frame.session_id or self.session_id
        event = self.extractor.to_event(session_id=session_id, features=features)
        return self.runtime_coordinator.process_event(event)
