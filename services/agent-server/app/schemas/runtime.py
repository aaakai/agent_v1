from __future__ import annotations

from time import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _new_id() -> str:
    return uuid4().hex


def _now_ms() -> int:
    return int(time() * 1000)


def _require_non_empty(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("must not be empty")
    return value


class Event(BaseModel):
    event_id: str = Field(default_factory=_new_id)
    session_id: str
    type: str
    timestamp_ms: int = Field(default_factory=_now_ms)
    source: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("session_id", "type")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        return _require_non_empty(value)


class OutputProposal(BaseModel):
    proposal_id: str = Field(default_factory=_new_id)
    session_id: str
    agent: str
    lane: str
    action: str
    text: str | None = None
    priority: int = 50
    timing: dict[str, Any] = Field(default_factory=dict)
    interrupt_policy: dict[str, Any] = Field(default_factory=dict)
    mixing: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("session_id", "agent", "lane", "action")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        return _require_non_empty(value)


class ControlAction(BaseModel):
    action_id: str = Field(default_factory=_new_id)
    session_id: str
    agent: str
    action: str
    priority: int = 50
    reason: str | None = None
    target: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("session_id", "agent", "action")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        return _require_non_empty(value)


class StateUpdate(BaseModel):
    update_id: str = Field(default_factory=_new_id)
    session_id: str
    agent: str
    patch: dict[str, Any]
    timestamp_ms: int = Field(default_factory=_now_ms)

    @field_validator("session_id", "agent")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        return _require_non_empty(value)


class AudioState(BaseModel):
    is_speaking: bool = False
    energy: float | None = None
    pause_ms: int = 0
    emotion: str | None = None
    backchannel_opportunity: float = 0.0
    barge_in_score: float = 0.0


class ASRState(BaseModel):
    partial: str | None = None
    final: str | None = None
    stability: float = 0.0
    updated_at_ms: int | None = None


class AssistantState(BaseModel):
    is_speaking: bool = False
    current_output: dict[str, Any] | None = None
    speech_lane_busy: bool = False


class SceneState(BaseModel):
    name: str = "default"
    mood: str | None = None
    ambience: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AudioRuntimeState(BaseModel):
    speech_lane_busy: bool = False
    sfx_playing: list[Any] = Field(default_factory=list)
    ambience_playing: str | None = None


class SessionState(BaseModel):
    session_id: str
    turn_id: str | None = None
    user_audio: AudioState = Field(default_factory=AudioState)
    asr: ASRState = Field(default_factory=ASRState)
    assistant: AssistantState = Field(default_factory=AssistantState)
    scene: SceneState = Field(default_factory=SceneState)
    audio_runtime: AudioRuntimeState = Field(default_factory=AudioRuntimeState)
    events: list[Event] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("session_id")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        return _require_non_empty(value)
