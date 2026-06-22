from __future__ import annotations

from time import time
from typing import Any

from pydantic import BaseModel, Field


def _now_ms() -> int:
    return int(time() * 1000)


class TurnState(BaseModel):
    is_user_speaking: bool = False
    last_speech_timestamp_ms: int | None = None
    last_silence_timestamp_ms: int | None = None
    turn_start_timestamp_ms: int | None = None
    silence_ms: int = 0
    speech_started: bool = False
    turn_open: bool = False
    turn_final_emitted: bool = False
    last_flush_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnDetectionResult(BaseModel):
    should_flush_asr: bool
    reason: str | None = None
    silence_ms: int = 0
    is_user_speaking: bool = False
    turn_open: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnDetector:
    def __init__(
        self,
        silence_flush_ms: int = 700,
        min_speech_ms: int = 200,
        max_turn_ms: int = 15000,
        reset_after_flush: bool = True,
    ) -> None:
        self.silence_flush_ms = silence_flush_ms
        self.min_speech_ms = min_speech_ms
        self.max_turn_ms = max_turn_ms
        self.reset_after_flush = reset_after_flush
        self.state = TurnState()

    def update_from_features(self, features: dict[str, Any]) -> TurnDetectionResult:
        timestamp_ms = int(features.get("timestamp_ms") or _now_ms())
        is_speaking = bool(features.get("is_speaking", False))
        self.state.is_user_speaking = is_speaking

        if is_speaking:
            if not self.state.turn_open:
                self.state.turn_start_timestamp_ms = timestamp_ms
            self.state.turn_open = True
            self.state.speech_started = True
            self.state.last_speech_timestamp_ms = timestamp_ms
            self.state.silence_ms = 0
            self.state.turn_final_emitted = False
            self.state.last_flush_reason = None
            return self._result(False, None)

        self.state.last_silence_timestamp_ms = timestamp_ms
        if not self.state.turn_open:
            return self._result(False, None)

        pause_ms = features.get("pause_ms")
        if pause_ms is not None:
            self.state.silence_ms = int(pause_ms)
        elif self.state.last_speech_timestamp_ms is not None:
            self.state.silence_ms = max(0, timestamp_ms - self.state.last_speech_timestamp_ms)
        else:
            self.state.silence_ms = 0

        if (
            self.state.silence_ms >= self.silence_flush_ms
            and not self.state.turn_final_emitted
        ):
            return self._flush_result("silence")
        return self._result(False, None)

    def update_from_user_speech_end(
        self,
        timestamp_ms: int | None = None,
    ) -> TurnDetectionResult:
        if timestamp_ms is not None:
            self.state.last_silence_timestamp_ms = timestamp_ms
        if self.state.turn_open or self.state.speech_started:
            return self._flush_result("user_speech_end")
        return self._result(False, None)

    def update_from_timeout(
        self,
        timestamp_ms: int | None = None,
    ) -> TurnDetectionResult:
        now_ms = timestamp_ms or _now_ms()
        if not self.state.turn_open or self.state.turn_start_timestamp_ms is None:
            return self._result(False, None)
        if now_ms - self.state.turn_start_timestamp_ms >= self.max_turn_ms:
            return self._flush_result("max_turn_duration")
        return self._result(False, None)

    def reset(self) -> None:
        self.state = TurnState()

    def snapshot(self) -> dict[str, Any]:
        data = self.state.model_dump(mode="python")
        data.update(
            {
                "silence_flush_ms": self.silence_flush_ms,
                "min_speech_ms": self.min_speech_ms,
                "max_turn_ms": self.max_turn_ms,
            }
        )
        return data

    def _flush_result(self, reason: str) -> TurnDetectionResult:
        self.state.turn_final_emitted = True
        self.state.last_flush_reason = reason
        result = self._result(True, reason)
        if self.reset_after_flush:
            self.state.turn_open = False
            self.state.is_user_speaking = False
        return result

    def _result(
        self,
        should_flush: bool,
        reason: str | None,
    ) -> TurnDetectionResult:
        return TurnDetectionResult(
            should_flush_asr=should_flush,
            reason=reason,
            silence_ms=self.state.silence_ms,
            is_user_speaking=self.state.is_user_speaking,
            turn_open=self.state.turn_open,
            metadata={"last_flush_reason": self.state.last_flush_reason},
        )
