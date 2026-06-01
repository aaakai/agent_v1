from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from presets import get_scene_preset
from schemas import OutputProposal


class SpatialPosition(BaseModel):
    azimuth_deg: float = 0.0
    elevation_deg: float = 0.0
    distance_m: float = 1.0


class SpatialPlan(BaseModel):
    event_id: str | None = None
    position: SpatialPosition
    movement: dict[str, Any] | None = None
    reverb: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


EVENT_POSITIONS: dict[str, SpatialPosition] = {
    "door_knock": SpatialPosition(azimuth_deg=-30, distance_m=2.5),
    "footsteps_indoor": SpatialPosition(azimuth_deg=45, distance_m=3.0),
    "cup_hit": SpatialPosition(azimuth_deg=10, distance_m=1.2),
}


def default_spatial_for_event(
    event: str,
    scene_name: str | None = None,
) -> SpatialPlan:
    preset = get_scene_preset(scene_name) if scene_name else None
    position = EVENT_POSITIONS.get(
        event,
        SpatialPosition(azimuth_deg=0, distance_m=1.5),
    )
    return SpatialPlan(
        event_id=event,
        position=position,
        reverb=preset.reverb if preset else "small_room",
    )


def attach_spatial_to_proposal(
    proposal: OutputProposal,
    scene_name: str | None = None,
) -> OutputProposal:
    if proposal.lane.lower() != "sfx" or proposal.action.upper() != "PLAY_SFX":
        return proposal

    event = proposal.metadata.get("event", "unknown")
    plan = default_spatial_for_event(event, scene_name=scene_name)
    metadata = dict(proposal.metadata)
    metadata["spatial"] = {
        **plan.position.model_dump(mode="python"),
        "reverb": plan.reverb,
    }
    return proposal.model_copy(update={"metadata": metadata}, deep=True)
