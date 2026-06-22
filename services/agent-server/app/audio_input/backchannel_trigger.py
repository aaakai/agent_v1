from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
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
        on_features: Callable[[dict[str, Any]], Any | Awaitable[Any]] | None = None,
    ) -> None:
        self.session_id = session_id
        self.runtime_coordinator = runtime_coordinator
        self.extractor = extractor or AudioFeatureExtractor()
        self.on_features = on_features

    async def consume(self, frame: AudioFrame) -> list[dict[str, Any]]:
        features = self.extractor.extract(frame)
        session_id = frame.session_id or self.session_id
        event = self.extractor.to_event(session_id=session_id, features=features)
        decisions = self.runtime_coordinator.process_event(event)
        if self.on_features is not None:
            extra = self.on_features(features)
            if inspect.isawaitable(extra):
                extra = await extra
            if isinstance(extra, list):
                decisions.extend(item for item in extra if isinstance(item, dict))
            elif isinstance(extra, dict):
                decisions.append(extra)
        return decisions
