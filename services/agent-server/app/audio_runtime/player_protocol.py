from __future__ import annotations

from time import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid4().hex


def _now_ms() -> int:
    return int(time() * 1000)


class PlayerCommand(BaseModel):
    command_id: str = Field(default_factory=_new_id)
    session_id: str
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp_ms: int = Field(default_factory=_now_ms)
    metadata: dict[str, Any] = Field(default_factory=dict)


def command_from_decision(decision: dict[str, Any]) -> PlayerCommand | None:
    decision_name = decision.get("decision")
    lane = decision.get("lane")
    command_type: str | None = None

    if decision_name == "play" and lane == "sfx":
        command_type = "PLAY_SFX"
    elif decision_name in {"play", "replace"} and lane == "ambience":
        command_type = "SET_AMBIENCE"
    elif decision_name == "duck":
        command_type = "DUCK_AUDIO"
    elif decision_name == "stop" and lane == "speech":
        command_type = "STOP_TTS"
    elif decision_name == "play" and lane == "speech":
        action = decision.get("proposal_action") or decision.get("action")
        command_type = "PLAY_BACKCHANNEL" if action == "BACKCHANNEL" else "PLAY_TTS"

    if command_type is None:
        return None

    return PlayerCommand(
        session_id=decision.get("session_id", ""),
        type=command_type,
        payload=dict(decision),
        metadata={
            "decision": decision_name,
            "lane": lane,
        },
    )


def commands_from_decisions(decisions: list[dict[str, Any]]) -> list[PlayerCommand]:
    commands: list[PlayerCommand] = []
    for decision in decisions:
        command = command_from_decision(decision)
        if command is not None:
            commands.append(command)
    return commands
