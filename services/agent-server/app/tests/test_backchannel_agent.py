from __future__ import annotations

from agents import MockBackchannelAgent
from schemas import SessionState


def test_backchannel_opportunity_produces_proposal() -> None:
    agent = MockBackchannelAgent()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True
    state.user_audio.backchannel_opportunity = 0.8

    result = agent.propose(state)

    assert len(result.proposals) == 1
    proposal = result.proposals[0]
    assert proposal.session_id == "session-1"
    assert proposal.agent == "backchannel"
    assert proposal.lane == "speech"
    assert proposal.action == "BACKCHANNEL"
    assert proposal.text == "嗯，我懂"
    assert proposal.priority == 30
    assert proposal.timing == {"start_after_ms": 80, "max_duration_ms": 600}
    assert proposal.interrupt_policy == {
        "can_interrupt_user": False,
        "can_interrupt_assistant": False,
    }
    assert proposal.mixing == {"gain": 0.35}


def test_backchannel_does_not_propose_when_assistant_is_speaking() -> None:
    agent = MockBackchannelAgent()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True
    state.user_audio.backchannel_opportunity = 0.8
    state.assistant.is_speaking = True

    result = agent.propose(state)

    assert result.proposals == []


def test_backchannel_does_not_propose_when_opportunity_is_low() -> None:
    agent = MockBackchannelAgent()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True
    state.user_audio.backchannel_opportunity = 0.5

    result = agent.propose(state)

    assert result.proposals == []
