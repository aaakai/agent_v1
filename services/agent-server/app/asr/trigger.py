from __future__ import annotations

from typing import Any

from audio_input import AudioFrame
from runtime import RuntimeCoordinator
from schemas import Event
from schemas.event_types import ASR_FINAL, ASR_PARTIAL

from .base import ASRResult, BaseASRAdapter


class ASRTrigger:
    def __init__(
        self,
        session_id: str,
        runtime_coordinator: RuntimeCoordinator,
        asr_adapter: BaseASRAdapter,
        auto_start: bool = True,
    ) -> None:
        self.session_id = session_id
        self.runtime_coordinator = runtime_coordinator
        self.asr_adapter = asr_adapter
        self.auto_start = auto_start
        self.started = False
        self.results_emitted = 0

    async def start(self) -> None:
        await self.asr_adapter.start_stream(self.session_id)
        self.started = True

    def result_to_event(self, result: ASRResult) -> Event:
        event_type = ASR_FINAL if result.is_final else ASR_PARTIAL
        payload: dict[str, Any] = {
            "text": result.text,
            "stability": 1.0 if result.is_final else result.stability,
            "metadata": result.metadata,
        }
        event_kwargs: dict[str, Any] = {
            "session_id": result.session_id or self.session_id,
            "type": event_type,
            "source": "asr",
            "payload": payload,
        }
        if result.timestamp_ms is not None:
            event_kwargs["timestamp_ms"] = result.timestamp_ms
        return Event(**event_kwargs)

    async def consume(self, frame: AudioFrame) -> list[dict[str, Any]]:
        if self.auto_start and not self.started:
            await self.start()

        decisions: list[dict[str, Any]] = []
        results = await self.asr_adapter.send_audio(frame)
        for result in results:
            event = self.result_to_event(result)
            decisions.extend(self.runtime_coordinator.process_event(event))
            self.results_emitted += 1
        return decisions

    async def close(self) -> None:
        await self.asr_adapter.close()
