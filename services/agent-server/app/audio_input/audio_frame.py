from __future__ import annotations

from time import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _new_id() -> str:
    return uuid4().hex


def _now_ms() -> int:
    return int(time() * 1000)


class AudioFrame(BaseModel):
    session_id: str
    frame_id: str = Field(default_factory=_new_id)
    timestamp_ms: int = Field(default_factory=_now_ms)
    sample_rate: int = 16000
    channels: int = 1
    samples_per_channel: int | None = None
    pcm: bytes = b""
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        if self.samples_per_channel is None:
            return None
        return self.samples_per_channel / self.sample_rate * 1000

    @property
    def is_empty(self) -> bool:
        return len(self.pcm) == 0

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("session_id must not be empty")
        return value

    @field_validator("sample_rate", "channels")
    @classmethod
    def validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @field_validator("samples_per_channel")
    @classmethod
    def validate_samples_per_channel(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("samples_per_channel must not be negative")
        return value
