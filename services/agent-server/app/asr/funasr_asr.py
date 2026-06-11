from __future__ import annotations

from audio_input import AudioFrame

from .base import ASRProviderStatus, ASRResult, BaseASRAdapter
from .config import ASRProviderConfig


class FunASRASRAdapter(BaseASRAdapter):
    def __init__(self, config: ASRProviderConfig | None = None) -> None:
        self.config = config or ASRProviderConfig(provider="funasr")
        self.provider = config.normalized_provider()
        self.started = False
        self.closed = False
        self.results_emitted = 0
        self.last_error: str | None = None

    async def start_stream(self, session_id: str) -> None:
        if not self.config.is_configured():
            self.last_error = f"{self.provider} ASR config is incomplete"
            raise ValueError(self.last_error)
        self.started = True
        raise NotImplementedError(f"{self.provider} ASR streaming is not implemented yet")

    async def send_audio(self, frame: AudioFrame) -> list[ASRResult]:
        if not self.started:
            raise RuntimeError("ASR stream is not started")
        raise NotImplementedError(f"{self.provider} ASR streaming is not implemented yet")

    async def receive_results(self) -> list[ASRResult]:
        return []

    async def close(self) -> None:
        self.closed = True

    def get_status(self) -> ASRProviderStatus:
        return ASRProviderStatus(
            provider=self.provider,
            configured=self.config.is_configured(),
            streaming=True,
            connected=self.started and not self.closed,
            session_started=self.started,
            results_emitted=self.results_emitted,
            last_error=self.last_error,
            metadata={"config": self.config.to_safe_dict()},
        )
