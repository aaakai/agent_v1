from __future__ import annotations

from time import time
from typing import Any

from asr import ASRTrigger
from runtime import RuntimeCoordinator
from schemas import Event
from schemas.event_types import AUDIO_FEATURE_UPDATE, USER_SPEECH_END

from .audio_frame import AudioFrame
from .turn_detector import TurnDetector


def _now_ms() -> int:
    return int(time() * 1000)


class ASRFlushTrigger:
    def __init__(
        self,
        session_id: str,
        asr_trigger: ASRTrigger,
        turn_detector: TurnDetector | None = None,
        runtime_coordinator: RuntimeCoordinator | None = None,
    ) -> None:
        self.session_id = session_id
        self.asr_trigger = asr_trigger
        self.turn_detector = turn_detector or TurnDetector()
        self.runtime_coordinator = runtime_coordinator
        self.flush_count = 0
        self.last_flush_reason: str | None = None
        self.last_flush_at_ms: int | None = None
        self.last_decisions: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []

    async def consume_features(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        result = self.turn_detector.update_from_features(features)
        if not result.should_flush_asr:
            return []
        return await self.flush(result.reason or "silence")

    async def consume_event(self, event: Event | dict[str, Any]) -> list[dict[str, Any]]:
        parsed = event if isinstance(event, Event) else Event.model_validate(event)
        if parsed.type == AUDIO_FEATURE_UPDATE:
            return await self.consume_features(parsed.payload)
        if parsed.type == USER_SPEECH_END:
            result = self.turn_detector.update_from_user_speech_end(parsed.timestamp_ms)
            if result.should_flush_asr:
                return await self.flush(result.reason or "user_speech_end")
        return []

    async def consume_frame(self, frame: AudioFrame) -> list[dict[str, Any]]:
        if frame.metadata.get("force_turn_end"):
            return await self.flush(str(frame.metadata.get("flush_reason") or "debug_force_turn_end"))
        return []

    async def flush(self, reason: str = "manual") -> list[dict[str, Any]]:
        self.last_flush_reason = reason
        self.last_flush_at_ms = _now_ms()
        try:
            decisions = await self.asr_trigger.flush(reason=reason)
        except Exception as exc:  # noqa: BLE001 - keep router fan-out alive.
            error = {"type": "asr_flush_error", "error": str(exc), "reason": reason}
            self.errors.append(error)
            self.last_decisions = [error]
            return [error]
        self.flush_count += 1
        self.last_decisions = decisions
        for decision in decisions:
            if decision.get("type") == "asr_error":
                self.errors.append(decision)
        return decisions

    def get_status(self) -> dict[str, Any]:
        turn_detector = self.turn_detector.snapshot()
        return {
            "flush_count": self.flush_count,
            "last_flush_reason": self.last_flush_reason,
            "last_flush_at_ms": self.last_flush_at_ms,
            "turn_detector": turn_detector,
            "timeline": list(turn_detector.get("timeline", [])),
            "errors": list(self.errors),
        }
