from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


class ASRProviderConfig(BaseModel):
    provider: str = "mock"
    language: str = "zh"
    sample_rate: int = 16000
    channels: int = 1
    model: str | None = None
    endpoint: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    interim_results: bool = True
    vad_events: bool = False
    chunk_duration_ms: int = 1500
    min_chunk_duration_ms: int = 500
    max_buffer_duration_ms: int = 5000
    openai_response_format: str = "json"
    openai_prompt: str | None = None
    openai_temperature: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "ASRProviderConfig":
        provider = os.getenv("ASR_PROVIDER") or "mock"
        normalized = provider.lower()
        api_key = os.getenv("ASR_API_KEY")
        endpoint = os.getenv("ASR_ENDPOINT")

        if normalized == "openai" and not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        elif normalized == "deepgram" and not api_key:
            api_key = os.getenv("DEEPGRAM_API_KEY")
        elif normalized == "funasr" and not endpoint:
            endpoint = os.getenv("FUNASR_ENDPOINT")
        elif normalized == "sensevoice" and not endpoint:
            endpoint = os.getenv("SENSEVOICE_ENDPOINT")
        model = os.getenv("ASR_MODEL")
        if normalized == "openai" and not model:
            model = "gpt-4o-mini-transcribe"

        return cls(
            provider=provider,
            language=os.getenv("ASR_LANGUAGE") or "zh",
            sample_rate=int(os.getenv("ASR_SAMPLE_RATE") or "16000"),
            channels=int(os.getenv("ASR_CHANNELS") or "1"),
            model=model,
            endpoint=endpoint,
            api_key=api_key,
            api_secret=os.getenv("ASR_API_SECRET"),
            chunk_duration_ms=int(os.getenv("ASR_CHUNK_DURATION_MS") or "1500"),
            min_chunk_duration_ms=int(os.getenv("ASR_MIN_CHUNK_DURATION_MS") or "500"),
            max_buffer_duration_ms=int(os.getenv("ASR_MAX_BUFFER_DURATION_MS") or "5000"),
            openai_response_format=os.getenv("OPENAI_ASR_RESPONSE_FORMAT") or "json",
            openai_prompt=os.getenv("OPENAI_ASR_PROMPT"),
            openai_temperature=_optional_float(os.getenv("OPENAI_ASR_TEMPERATURE")),
        )

    def normalized_provider(self) -> str:
        return self.provider.lower().strip()

    def with_env_credentials(self) -> "ASRProviderConfig":
        provider = self.normalized_provider()
        updates: dict[str, Any] = {}
        if provider == "openai" and not self.api_key:
            updates["api_key"] = os.getenv("ASR_API_KEY") or os.getenv("OPENAI_API_KEY")
        if provider == "openai" and not self.model:
            updates["model"] = os.getenv("ASR_MODEL") or "gpt-4o-mini-transcribe"
        if provider == "deepgram" and not self.api_key:
            updates["api_key"] = os.getenv("ASR_API_KEY") or os.getenv("DEEPGRAM_API_KEY")
        elif provider == "funasr" and not self.endpoint:
            updates["endpoint"] = os.getenv("ASR_ENDPOINT") or os.getenv("FUNASR_ENDPOINT")
        elif provider == "sensevoice" and not self.endpoint:
            updates["endpoint"] = os.getenv("ASR_ENDPOINT") or os.getenv("SENSEVOICE_ENDPOINT")
        return self.model_copy(update=updates) if updates else self

    def is_configured(self) -> bool:
        return not self.missing_fields()

    def missing_fields(self) -> list[str]:
        provider = self.normalized_provider()
        if provider in {"mock", "disabled"}:
            return []
        if provider in {"openai", "deepgram"}:
            return [] if self.api_key else ["api_key"]
        if provider in {"funasr", "sensevoice"}:
            return [] if self.endpoint else ["endpoint"]
        return ["provider"]

    def to_safe_dict(self) -> dict[str, Any]:
        metadata = {
            key: value
            for key, value in self.metadata.items()
            if "key" not in key.lower() and "secret" not in key.lower()
        }
        return {
            "provider": self.normalized_provider(),
            "language": self.language,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "model": self.model,
            "endpoint": self.endpoint,
            "api_key": "***" if self.api_key else None,
            "api_secret": "***" if self.api_secret else None,
            "interim_results": self.interim_results,
            "vad_events": self.vad_events,
            "chunk_duration_ms": self.chunk_duration_ms,
            "min_chunk_duration_ms": self.min_chunk_duration_ms,
            "max_buffer_duration_ms": self.max_buffer_duration_ms,
            "openai_response_format": self.openai_response_format,
            "openai_prompt": self.openai_prompt,
            "openai_temperature": self.openai_temperature,
            "configured": self.is_configured(),
            "missing_fields": self.missing_fields(),
            "metadata": metadata,
        }


def _optional_float(value: str | None) -> float | None:
    return float(value) if value not in {None, ""} else None
