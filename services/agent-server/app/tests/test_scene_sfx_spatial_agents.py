from __future__ import annotations

from agents import MockSceneAgent, MockSFXPlannerAgent, MockSpatialAudioAgent
from schemas import OutputProposal, SessionState


def test_scene_agent_emits_state_update_for_default_scene() -> None:
    agent = MockSceneAgent()
    state = SessionState(session_id="session-1")

    result = agent.propose(state)

    assert len(result.state_updates) == 1
    update = result.state_updates[0]
    assert update.agent == "scene"
    assert update.patch == {
        "scene": {
            "name": "office_meeting",
            "mood": "focused",
            "ambience": "office_room_tone",
            "metadata": {"reverb": "small_room"},
        }
    }


def test_scene_agent_is_empty_for_non_default_scene() -> None:
    agent = MockSceneAgent()
    state = SessionState(session_id="session-1")
    state.scene.name = "office_meeting"

    result = agent.propose(state)

    assert result.state_updates == []


def test_sfx_planner_emits_play_sfx_for_knock_text() -> None:
    agent = MockSFXPlannerAgent()
    state = SessionState(session_id="session-1")
    state.asr.final = "刚才好像有人敲门"

    result = agent.propose(state)

    assert len(result.proposals) == 1
    proposal = result.proposals[0]
    assert proposal.agent == "sfx_planner"
    assert proposal.lane == "sfx"
    assert proposal.action == "PLAY_SFX"
    assert proposal.priority == 20
    assert proposal.metadata == {
        "event": "door_knock",
        "asset_query": {
            "tags": ["door", "knock", "indoor"],
            "duration_ms": [300, 1200],
            "intensity": 0.7,
        },
    }
    assert proposal.timing == {"start_after_ms": 300}
    assert proposal.mixing == {"gain": 0.55, "duck_under_speech": True}


def test_sfx_planner_is_empty_without_keyword() -> None:
    agent = MockSFXPlannerAgent()
    state = SessionState(session_id="session-1")
    state.asr.final = "我们继续讨论架构"

    result = agent.propose(state)

    assert result.proposals == []


def test_spatial_audio_agent_enhances_sfx_metadata() -> None:
    agent = MockSpatialAudioAgent()
    state = SessionState(session_id="session-1")
    state.scene.metadata["reverb"] = "hall"
    proposal = OutputProposal(
        session_id="session-1",
        agent="sfx_planner",
        lane="sfx",
        action="PLAY_SFX",
        metadata={"event": "door_knock"},
    )

    enhanced = agent.enhance_sfx_proposal(proposal, state)

    assert enhanced is not proposal
    assert enhanced.metadata["event"] == "door_knock"
    assert enhanced.metadata["spatial"] == {
        "azimuth_deg": -30,
        "elevation_deg": 0,
        "distance_m": 2.5,
        "reverb": "hall",
    }


def test_spatial_audio_agent_leaves_non_sfx_proposal_unchanged() -> None:
    agent = MockSpatialAudioAgent()
    state = SessionState(session_id="session-1")
    proposal = OutputProposal(
        session_id="session-1",
        agent="dialogue",
        lane="speech",
        action="SPEAK",
        metadata={"kind": "dialogue"},
    )

    enhanced = agent.enhance_sfx_proposal(proposal, state)

    assert enhanced is proposal
    assert "spatial" not in enhanced.metadata


def test_spatial_audio_agent_uses_scene_reverb() -> None:
    agent = MockSpatialAudioAgent()
    state = SessionState(session_id="session-1")
    state.scene.name = "rainy_alley"
    proposal = OutputProposal(
        session_id="session-1",
        agent="sfx_planner",
        lane="sfx",
        action="PLAY_SFX",
        metadata={"event": "door_knock"},
    )

    enhanced = agent.enhance_sfx_proposal(proposal, state)

    assert enhanced.metadata["spatial"]["reverb"] == "wet_alley"
