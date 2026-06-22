from __future__ import annotations

import io
from time import time
from typing import Any

from audio_input import AudioFrame

from .base import ASRProviderStatus, ASRResult, BaseASRAdapter
from .config import ASRProviderConfig
from .wav_utils import estimate_audio_duration_ms, pcm_frames_to_wav_bytes


class OpenAIChunkedASRAdapter(BaseASRAdapter):
    provider = "openai"

    def __init__(
        self,
        config: ASRProviderConfig | None = None,
        client: Any | None = None,
    ) -> None:
        self.config = config or ASRProviderConfig(provider="openai")
        self.client = client
        self.session_id: str | None = None
        self.last_frame_session_id: str | None = None
        self.started = False
        self.closed = False
        self.buffer: list[AudioFrame] = []
        self.buffer_duration_ms = 0
        self.frames_sent = 0
        self.requests_sent = 0
        self.results_emitted = 0
        self.last_text: str | None = None
        self.last_error: str | None = None

    async def start_stream(self, session_id: str) -> None:
        if not self.config.is_configured():
            self.last_error = "OpenAI ASR config is incomplete"
            raise ValueError(self.last_error)
        self.session_id = session_id
        self.started = True

    async def send_audio(self, frame: AudioFrame) -> list[ASRResult]:
        self._ensure_ready()
        self.buffer.append(frame)
        self.last_frame_session_id = frame.session_id
        self.frames_sent += 1
        self.buffer_duration_ms = estimate_audio_duration_ms(self.buffer)
        if self.buffer_duration_ms < self.config.chunk_duration_ms:
            return []
        return await self._transcribe_and_clear()

    async def flush(self) -> list[ASRResult]:
        self._ensure_ready()
        if self.buffer_duration_ms < self.config.min_chunk_duration_ms:
            return []
        return await self._transcribe_and_clear()

    async def receive_results(self) -> list[ASRResult]:
        return []

    async def close(self) -> None:
        self.closed = True
        self.buffer = []
        self.buffer_duration_ms = 0

    async def transcribe_buffer(self) -> str:
        wav_bytes = pcm_frames_to_wav_bytes(
            self.buffer,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
        )
        self.requests_sent += 1
        started_at_ms = int(time() * 1000)
        try:
            text = await self._transcribe_wav_bytes(wav_bytes)
        except Exception as exc:
            self.last_error = str(exc)
            raise
        self.last_text = text
        self.last_error = None
        self._last_latency_ms = int(time() * 1000) - started_at_ms
        return text

    async def _transcribe_wav_bytes(self, wav_bytes: bytes) -> str:
        client = self.client or self._create_openai_client()
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "audio.wav"
        kwargs = self._build_transcription_kwargs(audio_file)
        response = client.audio.transcriptions.create(**kwargs)
        return self._extract_text_from_response(response).strip()

    def _build_transcription_kwargs(self, audio_file: Any) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.config.model or "gpt-4o-mini-transcribe",
            "file": audio_file,
            "language": self.config.language,
            "response_format": self.config.openai_response_format,
        }
        if self.config.openai_prompt is not None:
            kwargs["prompt"] = self.config.openai_prompt
        if self.config.openai_temperature is not None:
            kwargs["temperature"] = self.config.openai_temperature
        return kwargs

    def _extract_text_from_response(self, response: Any) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            return str(response.get("text") or response.get("output_text") or "")
        text = getattr(response, "text", None)
        if text is not None:
            return str(text)
        output_text = getattr(response, "output_text", None)
        if output_text is not None:
            return str(output_text)
        return ""

    def get_status(self) -> ASRProviderStatus:
        return ASRProviderStatus(
            provider="openai",
            configured=self.config.is_configured(),
            streaming=False,
            connected=self.started and not self.closed,
            session_started=self.started,
            results_emitted=self.results_emitted,
            finals_emitted=self.results_emitted,
            last_text=self.last_text,
            last_error=self.last_error,
            metadata={
                "mode": "chunked_transcription",
                "model": self.config.model,
                "chunk_duration_ms": self.config.chunk_duration_ms,
                "buffer_duration_ms": self.buffer_duration_ms,
                "frames_sent": self.frames_sent,
                "requests_sent": self.requests_sent,
                "closed": self.closed,
                "config": self.config.to_safe_dict(),
            },
        )

    async def _transcribe_and_clear(self) -> list[ASRResult]:
        text = await self.transcribe_buffer()
        latency_ms = getattr(self, "_last_latency_ms", None)
        self.buffer = []
        self.buffer_duration_ms = 0
        if not text:
            return []
        self.results_emitted += 1
        return [
            ASRResult(
                session_id=self.last_frame_session_id or self.session_id or "__openai__",
                text=text,
                is_final=True,
                stability=1.0,
                provider="openai",
                language=self.config.language,
                latency_ms=latency_ms,
                metadata={"mode": "chunked_transcription"},
            )
        ]

    def _ensure_ready(self) -> None:
        if self.closed:
            raise RuntimeError("ASR adapter is closed")
        if not self.started:
            raise RuntimeError("ASR stream is not started")

    def _create_openai_client(self) -> Any:
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001 - optional SDK.
            raise RuntimeError(
                "OpenAI SDK is not installed. Install openai to enable real ASR."
            ) from exc
        return OpenAI(api_key=self.config.api_key)


class OpenAIRealtimeASRAdapter(OpenAIChunkedASRAdapter):
    """Backward-compatible name for the current chunked OpenAI ASR adapter."""
