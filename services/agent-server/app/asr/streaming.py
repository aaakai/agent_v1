from __future__ import annotations

from typing import Any

from audio_input import AudioFrame

from .base import ASRProviderStatus, ASRResult, BaseASRAdapter


class MockStreamingASRAdapter(BaseASRAdapter):
    def __init__(
        self,
        scripted_results: list[ASRResult | dict[str, Any]] | None = None,
        partial_interval_frames: int = 1,
        final_after_frames: int | None = None,
        default_text: str = "",
        provider_name: str = "mock_streaming",
    ) -> None:
        self.provider_name = provider_name
        self.queue = [
            result if isinstance(result, ASRResult) else self._coerce_result(result)
            for result in (scripted_results or [])
        ]
        self.partial_interval_frames = max(1, partial_interval_frames)
        self.final_after_frames = final_after_frames
        self.default_text = default_text
        self.session_id = ""
        self.started = False
        self.closed = False
        self.frames_sent = 0
        self.results_emitted = 0
        self.partials_emitted = 0
        self.finals_emitted = 0
        self.last_text: str | None = None

    async def start_stream(self, session_id: str) -> None:
        self.session_id = session_id
        self.started = True

    async def send_audio(self, frame: AudioFrame) -> list[ASRResult]:
        self.frames_sent += 1
        if self.queue:
            return self._emit([self._with_frame_defaults(self.queue.pop(0), frame)])

        if "asr_text" in frame.metadata:
            is_final = bool(frame.metadata.get("asr_final", False))
            result = ASRResult(
                session_id=frame.session_id,
                text=str(frame.metadata["asr_text"]),
                is_final=is_final,
                stability=1.0 if is_final else 0.7,
                timestamp_ms=frame.timestamp_ms,
                metadata=dict(frame.metadata.get("asr_metadata", {})),
                provider=self.provider_name,
            )
            return self._emit([result])

        if not self.default_text:
            return []

        if (
            self.final_after_frames is not None
            and self.frames_sent >= self.final_after_frames
        ):
            result = ASRResult(
                session_id=frame.session_id,
                text=self.default_text,
                is_final=True,
                timestamp_ms=frame.timestamp_ms,
                provider=self.provider_name,
            )
            return self._emit([result])

        if self.frames_sent % self.partial_interval_frames == 0:
            result = ASRResult(
                session_id=frame.session_id,
                text=self.default_text,
                is_final=False,
                stability=0.7,
                timestamp_ms=frame.timestamp_ms,
                provider=self.provider_name,
            )
            return self._emit([result])
        return []

    async def receive_results(self) -> list[ASRResult]:
        return []

    async def close(self) -> None:
        self.closed = True

    def get_status(self) -> ASRProviderStatus:
        return ASRProviderStatus(
            provider=self.provider_name,
            configured=True,
            streaming=True,
            connected=self.started and not self.closed,
            session_started=self.started,
            results_emitted=self.results_emitted,
            partials_emitted=self.partials_emitted,
            finals_emitted=self.finals_emitted,
            last_text=self.last_text,
            metadata={"frames_sent": self.frames_sent, "closed": self.closed},
        )

    def _emit(self, results: list[ASRResult]) -> list[ASRResult]:
        for result in results:
            self.results_emitted += 1
            self.last_text = result.text
            if result.is_final:
                self.finals_emitted += 1
            else:
                self.partials_emitted += 1
        return results

    def _with_frame_defaults(self, result: ASRResult, frame: AudioFrame) -> ASRResult:
        updates: dict[str, Any] = {}
        if result.session_id != frame.session_id:
            updates["session_id"] = frame.session_id
        if result.timestamp_ms is None:
            updates["timestamp_ms"] = frame.timestamp_ms
        if result.provider is None:
            updates["provider"] = self.provider_name
        return result.model_copy(update=updates) if updates else result

    def _coerce_result(self, result: dict[str, Any]) -> ASRResult:
        payload = dict(result)
        if not payload.get("session_id"):
            payload["session_id"] = "__scripted__"
        if payload.get("provider") is None:
            payload["provider"] = self.provider_name
        return ASRResult.model_validate(payload)
