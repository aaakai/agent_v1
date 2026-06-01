from __future__ import annotations

from audio_input import AudioFrame

from .base import ASRResult, BaseASRAdapter


class _NotImplementedASRAdapter(BaseASRAdapter):
    provider_name = "ASR provider"

    async def start_stream(self, session_id: str) -> None:
        raise NotImplementedError(f"{self.provider_name} is not implemented yet")

    async def send_audio(self, frame: AudioFrame) -> list[ASRResult]:
        raise NotImplementedError(f"{self.provider_name} is not implemented yet")

    async def receive_results(self) -> list[ASRResult]:
        raise NotImplementedError(f"{self.provider_name} is not implemented yet")

    async def close(self) -> None:
        raise NotImplementedError(f"{self.provider_name} is not implemented yet")


class OpenAIRealtimeASRAdapter(_NotImplementedASRAdapter):
    provider_name = "OpenAI Realtime ASR adapter"


class DeepgramASRAdapter(_NotImplementedASRAdapter):
    provider_name = "Deepgram ASR adapter"


class FunASRASRAdapter(_NotImplementedASRAdapter):
    provider_name = "FunASR adapter"
