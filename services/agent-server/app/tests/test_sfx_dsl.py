from __future__ import annotations

import pytest

from audio_runtime import SFXAssetQuery, SFXEvent, proposal_from_sfx_event, sfx_event_from_proposal
from schemas import OutputProposal


def test_sfx_proposal_converts_to_event() -> None:
    proposal = OutputProposal(
        session_id="session-1",
        agent="sfx_planner",
        lane="sfx",
        action="PLAY_SFX",
        timing={"start_after_ms": 300},
        mixing={"gain": 0.55},
        metadata={
            "event": "door_knock",
            "asset_query": {
                "tags": ["door", "knock"],
                "duration_ms": [300, 1200],
                "intensity": 0.7,
            },
            "spatial": {"azimuth_deg": -30},
        },
    )

    event = sfx_event_from_proposal(proposal)

    assert event.event == "door_knock"
    assert event.start_after_ms == 300
    assert event.asset_query.tags == ["door", "knock"]
    assert event.asset_query.duration_ms == (300, 1200)
    assert event.intensity == 0.7
    assert event.spatial == {"azimuth_deg": -30}
    assert event.mixing == {"gain": 0.55}


def test_sfx_event_converts_to_proposal() -> None:
    sfx_event = SFXEvent(
        event="door_knock",
        start_after_ms=250,
        asset_query=SFXAssetQuery(
            tags=["door"],
            duration_ms=(300, 1200),
            intensity=0.7,
        ),
        spatial={"distance_m": 2.5},
        mixing={"gain": 0.55},
    )

    proposal = proposal_from_sfx_event("session-1", sfx_event)

    assert proposal.session_id == "session-1"
    assert proposal.lane == "sfx"
    assert proposal.action == "PLAY_SFX"
    assert proposal.priority == 20
    assert proposal.timing == {"start_after_ms": 250}
    assert proposal.mixing == {"gain": 0.55}
    assert proposal.metadata["event"] == "door_knock"
    assert proposal.metadata["asset_query"]["duration_ms"] == (300, 1200)
    assert proposal.metadata["spatial"] == {"distance_m": 2.5}


def test_non_sfx_proposal_raises() -> None:
    proposal = OutputProposal(
        session_id="session-1",
        agent="dialogue",
        lane="speech",
        action="SPEAK",
    )

    with pytest.raises(ValueError, match="PLAY_SFX"):
        sfx_event_from_proposal(proposal)


def test_missing_sfx_event_raises() -> None:
    proposal = OutputProposal(
        session_id="session-1",
        agent="sfx_planner",
        lane="sfx",
        action="PLAY_SFX",
    )

    with pytest.raises(ValueError, match="metadata.event"):
        sfx_event_from_proposal(proposal)
