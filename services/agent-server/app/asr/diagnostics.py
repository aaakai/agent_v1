from __future__ import annotations

from time import time
from typing import Any

from pydantic import BaseModel, Field

from audio_input import AudioFrame

from .base import ASRProviderStatus, ASRResult
from .config import ASRProviderConfig


def _now_ms() -> int:
    return int(time() * 1000)


class ASRDiagnostics(BaseModel):
    provider: str
    configured: bool
    status: dict[str, Any] = Field(default_factory=dict)
    recent_results: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    frames_sent: int = 0
    results_emitted: int = 0
    flush_count: int = 0
    last_flush_reason: str | None = None
    flushes: list[dict[str, Any]] = Field(default_factory=list)


class ASRDiagnosticsStore:
    def __init__(self, max_events: int = 200) -> None:
        self.max_events = max_events
        self.events: list[dict[str, Any]] = []

    def record_frame(self, frame: AudioFrame) -> None:
        self._append(
            {
                "timestamp_ms": _now_ms(),
                "type": "frame",
                "frame_id": frame.frame_id,
                "session_id": frame.session_id,
                "audio": {
                    "timestamp_ms": frame.timestamp_ms,
                    "sample_rate": frame.sample_rate,
                    "channels": frame.channels,
                    "duration_ms": frame.duration_ms,
                    "is_empty": frame.is_empty,
                },
            }
        )

    def record_result(self, result: ASRResult) -> None:
        self._append(
            {
                "timestamp_ms": _now_ms(),
                "type": "result",
                "session_id": result.session_id,
                "text": result.text,
                "is_final": result.is_final,
                "stability": result.stability,
                "provider": result.provider,
                "language": result.language,
                "latency_ms": result.latency_ms,
            }
        )

    def record_error(
        self,
        error: Exception | str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._append(
            {
                "timestamp_ms": _now_ms(),
                "type": "error",
                "error": str(error),
                "metadata": dict(metadata or {}),
            }
        )

    def record_flush(
        self,
        reason: str,
        results_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._append(
            {
                "timestamp_ms": _now_ms(),
                "type": "flush",
                "reason": reason,
                "results_count": results_count,
                "metadata": dict(metadata or {}),
            }
        )

    def snapshot(
        self,
        status: ASRProviderStatus | None = None,
        config: ASRProviderConfig | None = None,
    ) -> dict[str, Any]:
        frames_sent = len([event for event in self.events if event["type"] == "frame"])
        recent_results = [
            event
            for event in self.events
            if event["type"] == "result"
        ][-20:]
        errors = [
            event
            for event in self.events
            if event["type"] == "error"
        ][-20:]
        flushes = [
            event
            for event in self.events
            if event["type"] == "flush"
        ][-20:]
        provider = status.provider if status else (config.normalized_provider() if config else "unknown")
        configured = status.configured if status else (config.is_configured() if config else False)
        diagnostics = ASRDiagnostics(
            provider=provider,
            configured=configured,
            status=status.model_dump(mode="python") if status else {},
            recent_results=recent_results,
            errors=errors,
            frames_sent=frames_sent,
            results_emitted=len(recent_results),
            flush_count=len([event for event in self.events if event["type"] == "flush"]),
            last_flush_reason=flushes[-1]["reason"] if flushes else None,
            flushes=flushes,
        )
        data = diagnostics.model_dump(mode="python")
        if config is not None:
            data["config"] = config.to_safe_dict()
        return data

    def reset(self) -> None:
        self.events = []

    def _append(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]
