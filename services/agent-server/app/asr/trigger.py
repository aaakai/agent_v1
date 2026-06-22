from __future__ import annotations

from time import time
from typing import Any

from audio_input import AudioFrame
from runtime import RuntimeCoordinator
from schemas import Event
from schemas.event_types import ASR_FINAL, ASR_PARTIAL

from .base import ASRResult, BaseASRAdapter
from .diagnostics import ASRDiagnosticsStore


def _now_ms() -> int:
    return int(time() * 1000)


class ASRTrigger:
    def __init__(
        self,
        session_id: str,
        runtime_coordinator: RuntimeCoordinator,
        asr_adapter: BaseASRAdapter,
        auto_start: bool = True,
        diagnostics: ASRDiagnosticsStore | None = None,
    ) -> None:
        self.session_id = session_id
        self.runtime_coordinator = runtime_coordinator
        self.asr_adapter = asr_adapter
        self.auto_start = auto_start
        self.diagnostics = diagnostics or ASRDiagnosticsStore()
        self.started = False
        self.results_emitted = 0
        self.flush_count = 0
        self.last_flush_reason: str | None = None
        self.provider_errors: list[dict[str, Any]] = []
        self.last_result: ASRResult | None = None

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
        self.diagnostics.record_frame(frame)
        if self.auto_start and not self.started:
            try:
                await self.start()
            except Exception as exc:  # noqa: BLE001 - provider failures are debug data.
                return [self._record_provider_error(exc)]

        decisions: list[dict[str, Any]] = []
        try:
            results = await self.asr_adapter.send_audio(frame)
        except Exception as exc:  # noqa: BLE001 - keep router fan-out alive.
            return [self._record_provider_error(exc)]
        for result in results:
            event = self.result_to_event(result)
            decisions.extend(self.runtime_coordinator.process_event(event))
            self.diagnostics.record_result(result)
            self.last_result = result
            self.results_emitted += 1
        return decisions

    async def close(self) -> None:
        await self.asr_adapter.close()

    async def flush(self, reason: str = "manual") -> list[dict[str, Any]]:
        flush = getattr(self.asr_adapter, "flush", None)
        if not callable(flush):
            return []
        flushed_at_ms = _now_ms()
        try:
            results = await flush()
        except Exception as exc:  # noqa: BLE001 - keep caller alive.
            return [self._record_provider_error(exc)]
        self.flush_count += 1
        self.last_flush_reason = reason
        self.diagnostics.record_flush(
            reason,
            len(results),
            metadata={"flushed_at_ms": flushed_at_ms},
        )
        decisions: list[dict[str, Any]] = []
        for result in results:
            metadata = dict(result.metadata)
            metadata.update(
                {
                    "flush_reason": reason,
                    "turn_final": True,
                    "flushed_at_ms": flushed_at_ms,
                }
            )
            result = result.model_copy(update={"metadata": metadata})
            event = self.result_to_event(result)
            decisions.extend(self.runtime_coordinator.process_event(event))
            self.diagnostics.record_result(result)
            self.last_result = result
            self.results_emitted += 1
        return decisions

    def get_status(self) -> dict[str, Any]:
        adapter_status = self.asr_adapter.get_status()
        return {
            "started": self.started,
            "results_emitted": self.results_emitted,
            "flush_count": self.flush_count,
            "last_flush_reason": self.last_flush_reason,
            "provider_errors": list(self.provider_errors),
            "last_result": self.last_result.model_dump(mode="python") if self.last_result else None,
            "adapter": adapter_status.model_dump(mode="python"),
            "diagnostics": self.diagnostics.snapshot(status=adapter_status),
        }

    def _record_provider_error(self, exc: Exception) -> dict[str, Any]:
        provider = self.asr_adapter.get_status().provider
        error = {
            "type": "asr_error",
            "provider": provider,
            "error": str(exc),
        }
        self.provider_errors.append(error)
        self.diagnostics.record_error(exc, metadata={"provider": provider})
        return error
