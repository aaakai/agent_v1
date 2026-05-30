from __future__ import annotations

from agents import MockBackchannelAgent, MockInterruptAgent, MockSFXPlannerAgent
from orchestrator import AudioOrchestrator
from schemas import OutputProposal, SessionState


def test_backchannel_agent_proposal_can_be_played_by_orchestrator() -> None:
    agent = MockBackchannelAgent()
    orchestrator = AudioOrchestrator()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True
    state.user_audio.backchannel_opportunity = 0.8

    result = agent.propose(state)
    decision = orchestrator.handle_output_proposal(
        result.proposals[0],
        state=state,
        now_ms=1000,
    )

    assert decision["decision"] == "play"
    assert decision["lane"] == "speech"


def test_interrupt_agent_stop_speaking_can_be_handled_by_orchestrator() -> None:
    agent = MockInterruptAgent()
    orchestrator = AudioOrchestrator()
    state = SessionState(session_id="session-1")
    speech = OutputProposal(
        session_id="session-1",
        agent="dialogue",
        lane="speech",
        action="SPEAK",
    )
    orchestrator.handle_output_proposal(speech, state=state, now_ms=1000)
    state.user_audio.is_speaking = True
    state.user_audio.barge_in_score = 0.8

    result = agent.propose(state)
    decision = orchestrator.handle_control_action(
        result.control_actions[0],
        state=state,
        now_ms=1200,
    )

    assert decision["decision"] == "stop"
    assert decision["lane"] == "speech"
    assert orchestrator.speech_lane.current is None


def test_sfx_planner_proposal_is_dispatched_to_sfx_lane() -> None:
    agent = MockSFXPlannerAgent()
    orchestrator = AudioOrchestrator()
    state = SessionState(session_id="session-1")
    state.asr.final = "门响了"

    result = agent.propose(state)
    decision = orchestrator.handle_output_proposal(
        result.proposals[0],
        state=state,
        now_ms=1000,
    )

    assert decision["decision"] == "play"
    assert decision["lane"] == "sfx"
    assert orchestrator.sfx_lane.active == [result.proposals[0]]
