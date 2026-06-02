from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SpeechPlaybackState(BaseModel):
    current: dict[str, Any] | None = None
    queue: list[dict[str, Any]] = Field(default_factory=list)
    stopped: bool = False
    ducked: bool = False
    last_command_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SFXPlaybackState(BaseModel):
    active: list[dict[str, Any]] = Field(default_factory=list)
    stopped: list[dict[str, Any]] = Field(default_factory=list)
    ducked: bool = False
    last_command_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AmbiencePlaybackState(BaseModel):
    current: dict[str, Any] | None = None
    ducked: bool = False
    stopped: bool = False
    last_command_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlaybackState(BaseModel):
    session_id: str
    speech: SpeechPlaybackState = Field(default_factory=SpeechPlaybackState)
    sfx: SFXPlaybackState = Field(default_factory=SFXPlaybackState)
    ambience: AmbiencePlaybackState = Field(default_factory=AmbiencePlaybackState)
    command_count: int = 0
    history: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="python")

    def reset(self) -> None:
        self.speech = SpeechPlaybackState()
        self.sfx = SFXPlaybackState()
        self.ambience = AmbiencePlaybackState()
        self.command_count = 0
        self.history = []
        self.metadata = {}

    def append_history(self, command_dict: dict[str, Any]) -> None:
        self.history.append(dict(command_dict))
