from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas import OutputProposal


class SFXAssetQuery(BaseModel):
    tags: list[str] = Field(default_factory=list)
    duration_ms: tuple[int, int] | None = None
    intensity: float = 0.5
    scene: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SFXEvent(BaseModel):
    event: str
    start_after_ms: int = 0
    intensity: float = 0.5
    asset_query: SFXAssetQuery
    spatial: dict[str, Any] = Field(default_factory=dict)
    mixing: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


def sfx_event_from_proposal(proposal: OutputProposal) -> SFXEvent:
    if proposal.lane.lower() != "sfx" or proposal.action.upper() != "PLAY_SFX":
        raise ValueError("proposal must be a PLAY_SFX proposal on the sfx lane")

    event_name = proposal.metadata.get("event")
    if not event_name:
        raise ValueError("sfx proposal metadata.event is required")

    raw_query = proposal.metadata.get("asset_query")
    if raw_query is None:
        raw_query = {
            "tags": proposal.metadata.get("tags", [event_name]),
            "intensity": proposal.metadata.get("intensity", 0.5),
        }

    query = SFXAssetQuery.model_validate(raw_query)
    return SFXEvent(
        event=event_name,
        start_after_ms=proposal.timing.get("start_after_ms", 0),
        intensity=query.intensity,
        asset_query=query,
        spatial=dict(proposal.metadata.get("spatial", {})),
        mixing=dict(proposal.mixing),
        metadata={
            key: value
            for key, value in proposal.metadata.items()
            if key not in {"event", "asset_query", "spatial"}
        },
    )


def proposal_from_sfx_event(
    session_id: str,
    event: SFXEvent,
    agent: str = "sfx_planner",
) -> OutputProposal:
    return OutputProposal(
        session_id=session_id,
        agent=agent,
        lane="sfx",
        action="PLAY_SFX",
        priority=20,
        timing={"start_after_ms": event.start_after_ms},
        mixing=dict(event.mixing),
        metadata={
            "event": event.event,
            "asset_query": event.asset_query.model_dump(mode="python"),
            "spatial": dict(event.spatial),
            **dict(event.metadata),
        },
    )
