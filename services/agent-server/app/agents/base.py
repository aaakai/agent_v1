from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas import ControlAction, Event, OutputProposal, SessionState, StateUpdate


class AgentResult(BaseModel):
    proposals: list[OutputProposal] = Field(default_factory=list)
    control_actions: list[ControlAction] = Field(default_factory=list)
    state_updates: list[StateUpdate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent:
    name: str

    def __init__(self, name: str | None = None) -> None:
        self.name = name or self.__class__.__name__

    def observe(self, event: Event, state: SessionState) -> AgentResult:
        return self.empty_result()

    def propose(self, state: SessionState) -> AgentResult:
        return self.empty_result()

    def empty_result(self) -> AgentResult:
        return AgentResult()

    def make_metadata(self, **extra: Any) -> dict[str, Any]:
        metadata: dict[str, Any] = {"agent": self.name}
        metadata.update(extra)
        return metadata
