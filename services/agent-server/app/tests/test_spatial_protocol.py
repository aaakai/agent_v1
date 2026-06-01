from __future__ import annotations

from audio_runtime import attach_spatial_to_proposal, default_spatial_for_event
from schemas import OutputProposal


def test_door_knock_default_spatial() -> None:
    plan = default_spatial_for_event("door_knock")

    assert plan.position.azimuth_deg == -30
    assert plan.position.distance_m == 2.5
    assert plan.reverb == "small_room"


def test_footsteps_default_spatial() -> None:
    plan = default_spatial_for_event("footsteps_indoor")

    assert plan.position.azimuth_deg == 45
    assert plan.position.distance_m == 3.0


def test_rainy_alley_reverb() -> None:
    plan = default_spatial_for_event("door_knock", scene_name="rainy_alley")

    assert plan.reverb == "wet_alley"


def test_attach_spatial_to_sfx_proposal() -> None:
    proposal = OutputProposal(
        session_id="session-1",
        agent="sfx_planner",
        lane="sfx",
        action="PLAY_SFX",
        metadata={"event": "door_knock"},
    )

    enhanced = attach_spatial_to_proposal(proposal, scene_name="rainy_alley")

    assert enhanced is not proposal
    assert enhanced.metadata["spatial"] == {
        "azimuth_deg": -30.0,
        "elevation_deg": 0.0,
        "distance_m": 2.5,
        "reverb": "wet_alley",
    }


def test_attach_spatial_ignores_non_sfx_proposal() -> None:
    proposal = OutputProposal(
        session_id="session-1",
        agent="dialogue",
        lane="speech",
        action="SPEAK",
    )

    assert attach_spatial_to_proposal(proposal) is proposal
