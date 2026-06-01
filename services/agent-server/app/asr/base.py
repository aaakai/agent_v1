from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from audio_input import AudioFrame


class ASRResult(BaseModel):
    session_id: str
    text: str = ""
    is_final: bool
    stability: float = 0.0
    timestamp_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("session_id must not be empty")
        return value

    @model_validator(mode="after")
    def default_final_stability(self) -> "ASRResult":
        if self.is_final and "stability" not in self.model_fields_set:
            self.stability = 1.0
        return self


class BaseASRAdapter:
    async def start_stream(self, session_id: str) -> None:
        return None

    async def send_audio(self, frame: AudioFrame) -> list[ASRResult]:
        return []

    async def receive_results(self) -> list[ASRResult]:
        return []

    async def close(self) -> None:
        return None
