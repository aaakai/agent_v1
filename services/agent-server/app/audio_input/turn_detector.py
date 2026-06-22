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
    timeline: list[dict[str, Any]] = Field(default_factory=list)
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
        self.max_timeline_items = 200

    def update_from_features(self, features: dict[str, Any]) -> TurnDetectionResult:
        timestamp_ms = int(features.get("timestamp_ms") or _now_ms())
        is_speaking = bool(features.get("is_speaking", False))
        self.state.is_user_speaking = is_speaking

        if is_speaking:
            is_new_turn = not self.state.turn_open
            if is_new_turn:
                self.state.turn_start_timestamp_ms = timestamp_ms
            self.state.turn_open = True
            self.state.speech_started = True
            self.state.last_speech_timestamp_ms = timestamp_ms
            self.state.silence_ms = 0
            self.state.turn_final_emitted = False
            self.state.last_flush_reason = None
            self._append_timeline(
                timestamp_ms=timestamp_ms,
                event_type="speech_start" if is_new_turn else "speech_frame",
                message="用户开始说话" if is_new_turn else "收到用户语音帧",
                metadata={
                    "energy": features.get("energy"),
                    "pause_ms": features.get("pause_ms"),
                },
            )
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
        self._append_timeline(
            timestamp_ms=timestamp_ms,
            event_type="silence",
            message=f"检测到静音 {self.state.silence_ms}ms",
            metadata={
                "silence_ms": self.state.silence_ms,
                "silence_flush_ms": self.silence_flush_ms,
                "energy": features.get("energy"),
            },
        )

        if (
            self.state.silence_ms >= self.silence_flush_ms
            and not self.state.turn_final_emitted
        ):
            return self._flush_result("silence", timestamp_ms=timestamp_ms)
        return self._result(False, None)

    def update_from_user_speech_end(
        self,
        timestamp_ms: int | None = None,
    ) -> TurnDetectionResult:
        active_timestamp_ms = timestamp_ms or _now_ms()
        self.state.last_silence_timestamp_ms = active_timestamp_ms
        self._append_timeline(
            timestamp_ms=active_timestamp_ms,
            event_type="turn_end",
            message="收到 USER_SPEECH_END，用户语音结束",
            metadata={"turn_open": self.state.turn_open},
        )
        if self.state.turn_open or self.state.speech_started:
            return self._flush_result("user_speech_end", timestamp_ms=active_timestamp_ms)
        return self._result(False, None)

    def update_from_timeout(
        self,
        timestamp_ms: int | None = None,
    ) -> TurnDetectionResult:
        now_ms = timestamp_ms or _now_ms()
        if not self.state.turn_open or self.state.turn_start_timestamp_ms is None:
            return self._result(False, None)
        if now_ms - self.state.turn_start_timestamp_ms >= self.max_turn_ms:
            self._append_timeline(
                timestamp_ms=now_ms,
                event_type="timeout",
                message="单轮说话达到最大时长",
                metadata={
                    "turn_duration_ms": now_ms - self.state.turn_start_timestamp_ms,
                    "max_turn_ms": self.max_turn_ms,
                },
            )
            return self._flush_result("max_turn_duration", timestamp_ms=now_ms)
        return self._result(False, None)

    def reset(self) -> None:
        timeline = list(self.state.timeline)
        self.state = TurnState()
        self.state.timeline = timeline
        self._append_timeline(
            timestamp_ms=_now_ms(),
            event_type="reset",
            message="TurnDetector 状态已重置",
            metadata={},
        )

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

    def _flush_result(
        self,
        reason: str,
        timestamp_ms: int | None = None,
    ) -> TurnDetectionResult:
        self.state.turn_final_emitted = True
        self.state.last_flush_reason = reason
        self._append_timeline(
            timestamp_ms=timestamp_ms or _now_ms(),
            event_type="flush",
            message=f"触发 ASR flush：{reason}",
            metadata={
                "reason": reason,
                "silence_ms": self.state.silence_ms,
                "turn_open": self.state.turn_open,
            },
        )
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

    def _append_timeline(
        self,
        timestamp_ms: int,
        event_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.state.timeline.append(
            {
                "timestamp_ms": timestamp_ms,
                "type": event_type,
                "message": message,
                "metadata": dict(metadata or {}),
            }
        )
        if len(self.state.timeline) > self.max_timeline_items:
            self.state.timeline = self.state.timeline[-self.max_timeline_items :]
