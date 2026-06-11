from __future__ import annotations

from audio_input import AudioFrame

from .base import ASRProviderStatus, ASRResult, BaseASRAdapter
from .config import ASRProviderConfig
from .deepgram_asr import DeepgramASRAdapter
from .funasr_asr import FunASRASRAdapter
from .openai_asr import OpenAIChunkedASRAdapter
from .streaming import MockStreamingASRAdapter


class DisabledASRAdapter(BaseASRAdapter):
    async def send_audio(self, frame: AudioFrame) -> list[ASRResult]:
        return []

    def get_status(self) -> ASRProviderStatus:
        return ASRProviderStatus(
            provider="disabled",
            configured=True,
            streaming=False,
        )


def create_asr_adapter(
    config: ASRProviderConfig | None = None,
) -> BaseASRAdapter:
    provider_config = config or ASRProviderConfig.from_env()
    provider = provider_config.normalized_provider()
    if provider == "mock":
        return MockStreamingASRAdapter(provider_name="mock")
    if provider == "disabled":
        return DisabledASRAdapter()
    if provider == "openai":
        return OpenAIChunkedASRAdapter(provider_config)
    if provider == "deepgram":
        return DeepgramASRAdapter(provider_config)
    if provider in {"funasr", "sensevoice"}:
        return FunASRASRAdapter(provider_config)
    raise ValueError(f"Unknown ASR provider: {provider_config.provider}")


def create_asr_adapter_from_env() -> BaseASRAdapter:
    return create_asr_adapter(ASRProviderConfig.from_env())
