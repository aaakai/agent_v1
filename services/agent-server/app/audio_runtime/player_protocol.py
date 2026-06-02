from __future__ import annotations

from dataclasses import asdict, is_dataclass
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
        proposal = decision.get("proposal")
        proposal_action = proposal.get("action") if isinstance(proposal, dict) else None
        action = decision.get("proposal_action") or proposal_action or decision.get("action")
        command_type = "PLAY_BACKCHANNEL" if action == "BACKCHANNEL" else "PLAY_TTS"

    if command_type is None:
        return None

    return PlayerCommand(
        session_id=decision.get("session_id", ""),
        type=command_type,
        payload=_payload_from_decision(decision, command_type),
        metadata={
            "decision": decision_name,
            "lane": lane,
        },
    )


def _payload_from_decision(
    decision: dict[str, Any],
    command_type: str,
) -> dict[str, Any]:
    payload = dict(decision)
    payload["original_decision"] = dict(decision)

    proposal = decision.get("proposal")
    if isinstance(proposal, dict):
        metadata = proposal.get("metadata", {})
        mixing = proposal.get("mixing", {})
        if isinstance(metadata, dict):
            for key in (
                "event",
                "asset",
                "asset_id",
                "path",
                "scene",
                "ambience",
                "spatial",
                "reverb",
            ):
                if key in metadata:
                    payload.setdefault(key, metadata[key])
            asset_query = metadata.get("asset_query")
            if asset_query is not None:
                payload.setdefault("asset_query", asset_query)
        if isinstance(mixing, dict):
            payload.setdefault("mixing", dict(mixing))
            for key in ("gain", "loop", "fade_ms", "duck_under_speech"):
                if key in mixing:
                    payload.setdefault(key, mixing[key])
        for key in ("text", "action", "agent", "priority", "lane"):
            if key in proposal:
                payload.setdefault(key, proposal[key])

    if command_type in {"PLAY_TTS", "PLAY_BACKCHANNEL"}:
        payload.setdefault("action", decision.get("proposal_action"))
        payload.setdefault("agent", decision.get("agent"))
        payload.setdefault("priority", decision.get("priority"))
    elif command_type == "STOP_TTS":
        payload.setdefault("reason", decision.get("reason"))
    elif command_type == "DUCK_AUDIO":
        payload.setdefault("target", decision.get("target"))
        payload.setdefault("reason", decision.get("reason"))

    return payload


def commands_from_decisions(decisions: list[dict[str, Any]]) -> list[PlayerCommand]:
    commands: list[PlayerCommand] = []
    for decision in decisions:
        command = command_from_decision(decision)
        if command is not None:
            commands.append(command)
    return commands


def command_to_dict(command: PlayerCommand) -> dict[str, Any]:
    if hasattr(command, "model_dump"):
        return command.model_dump(mode="python")
    if is_dataclass(command):
        return asdict(command)
    return dict(command)  # type: ignore[arg-type]


def commands_to_dict(commands: list[PlayerCommand]) -> list[dict[str, Any]]:
    return [command_to_dict(command) for command in commands]
