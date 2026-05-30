from __future__ import annotations

from orchestrator import AmbienceLane, SFXLane
from schemas import OutputProposal, SessionState


def sfx_proposal() -> OutputProposal:
    return OutputProposal(
        session_id="session-1",
        agent="sfx-agent",
        lane="sfx",
        action="PLAY_SFX",
        text="doorbell",
    )


def ambience_proposal(text: str) -> OutputProposal:
    return OutputProposal(
        session_id="session-1",
        agent="scene-agent",
        lane="ambience",
        action="SET_AMBIENCE",
        text=text,
    )


def test_sfx_can_play_and_tracks_active() -> None:
    lane = SFXLane()
    state = SessionState(session_id="session-1")
    proposal = sfx_proposal()

    decision = lane.apply_proposal(proposal, state, now_ms=1000)

    assert decision["decision"] == "play"
    assert decision["duck"] is False
    assert lane.active == [proposal]
    assert state.audio_runtime.sfx_playing[0]["proposal_id"] == proposal.proposal_id


def test_sfx_ducks_when_speech_is_busy() -> None:
    lane = SFXLane()
    state = SessionState(session_id="session-1")
    state.audio_runtime.speech_lane_busy = True

    decision = lane.apply_proposal(sfx_proposal(), state, now_ms=1000)

    assert decision["decision"] == "play"
    assert decision["duck"] is True


def test_sfx_duck_all_returns_duck_decision() -> None:
    lane = SFXLane()
    state = SessionState(session_id="session-1")
    proposal = sfx_proposal()
    lane.apply_proposal(proposal, state, now_ms=1000)

    decision = lane.duck_all("speech_started")

    assert decision["decision"] == "duck"
    assert decision["lane"] == "sfx"
    assert decision["duck"] is True
    assert decision["proposal_ids"] == [proposal.proposal_id]


def test_ambience_set_current_and_replace_existing() -> None:
    lane = AmbienceLane()
    state = SessionState(session_id="session-1")
    first = ambience_proposal("rain")
    second = ambience_proposal("city")

    first_decision = lane.apply_proposal(first, state, now_ms=1000)
    second_decision = lane.apply_proposal(second, state, now_ms=2000)

    assert first_decision["decision"] == "play"
    assert second_decision["decision"] == "replace"
    assert second_decision["replaced"]["proposal_id"] == first.proposal_id
    assert lane.current == second
    assert state.scene.ambience == "city"


def test_ambience_ducks_when_speech_is_busy() -> None:
    lane = AmbienceLane()
    state = SessionState(session_id="session-1")
    state.assistant.is_speaking = True

    decision = lane.apply_proposal(ambience_proposal("rain"), state, now_ms=1000)

    assert decision["decision"] == "play"
    assert decision["duck"] is True
