from __future__ import annotations

from audio_input import AudioFrame

from .base import ASRResult, BaseASRAdapter


class MockASRAdapter(BaseASRAdapter):
    def __init__(
        self,
        scripted_results: list[ASRResult] | list[dict] | None = None,
        emit_per_frame: bool = True,
    ) -> None:
        self.queue = [
            result if isinstance(result, ASRResult) else self._coerce_scripted_result(result)
            for result in (scripted_results or [])
        ]
        self.emit_per_frame = emit_per_frame
        self.started_sessions: set[str] = set()
        self.sent_frames: list[AudioFrame] = []
        self.closed = False

    async def start_stream(self, session_id: str) -> None:
        self.started_sessions.add(session_id)

    async def send_audio(self, frame: AudioFrame) -> list[ASRResult]:
        self.sent_frames.append(frame)
        if self.queue:
            result = self.queue.pop(0)
            if result.session_id != frame.session_id:
                result = result.model_copy(update={"session_id": frame.session_id})
            if result.timestamp_ms is None:
                result = result.model_copy(update={"timestamp_ms": frame.timestamp_ms})
            return [result]

        if not self.emit_per_frame or "asr_text" not in frame.metadata:
            return []

        is_final = bool(frame.metadata.get("asr_final", False))
        return [
            ASRResult(
                session_id=frame.session_id,
                text=str(frame.metadata["asr_text"]),
                is_final=is_final,
                stability=1.0 if is_final else 0.7,
                timestamp_ms=frame.timestamp_ms,
                metadata=dict(frame.metadata.get("asr_metadata", {})),
            )
        ]

    async def receive_results(self) -> list[ASRResult]:
        return []

    async def close(self) -> None:
        self.closed = True

    def _coerce_scripted_result(self, result: dict) -> ASRResult:
        payload = dict(result)
        if not payload.get("session_id"):
            payload["session_id"] = "__scripted__"
        return ASRResult.model_validate(payload)
