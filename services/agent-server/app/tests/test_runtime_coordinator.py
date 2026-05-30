from __future__ import annotations

from agents import AgentResult, BaseAgent
from runtime import RuntimeCoordinator
from schemas import Event, OutputProposal, SessionState
from schemas.event_types import (
    ASR_FINAL,
    ASR_PARTIAL,
    AUDIO_FEATURE_UPDATE,
    USER_SPEECH_END,
    USER_SPEECH_START,
)


class ProposalAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="proposal_agent")
        self.observed = 0
        self.proposed = 0

    def observe(self, event: Event, state: SessionState) -> AgentResult:
        self.observed += 1
        return self.empty_result()

    def propose(self, state: SessionState) -> AgentResult:
        self.proposed += 1
        return AgentResult(
            proposals=[
                OutputProposal(
                    session_id=state.session_id,
                    agent="dialogue",
                    lane="speech",
                    action="SPEAK",
                    text="agent says hello",
                )
            ]
        )


def test_user_speech_start_updates_user_audio_state() -> None:
    coordinator = RuntimeCoordinator()

    coordinator.process_event(
        Event(session_id="session-1", type=USER_SPEECH_START)
    )

    assert coordinator.get_session_state("session-1").user_audio.is_speaking is True


def test_asr_partial_and_final_update_state() -> None:
    coordinator = RuntimeCoordinator()

    coordinator.process_event(
        Event(
            session_id="session-1",
            type=ASR_PARTIAL,
            timestamp_ms=100,
            payload={"text": "hello", "stability": 0.4},
        )
    )
    partial_state = coordinator.get_session_state("session-1")
    coordinator.process_event(
        Event(
            session_id="session-1",
            type=ASR_FINAL,
            timestamp_ms=200,
            payload={"text": "hello world"},
        )
    )
    final_state = coordinator.get_session_state("session-1")

    assert partial_state.asr.partial == "hello"
    assert partial_state.asr.stability == 0.4
    assert partial_state.asr.updated_at_ms == 100
    assert final_state.asr.final == "hello world"
    assert final_state.asr.partial is None
    assert final_state.asr.stability == 1.0
    assert final_state.asr.updated_at_ms == 200


def test_audio_feature_update_updates_user_audio_features() -> None:
    coordinator = RuntimeCoordinator()

    coordinator.process_event(
        Event(
            session_id="session-1",
            type=AUDIO_FEATURE_UPDATE,
            payload={
                "backchannel_opportunity": 0.85,
                "barge_in_score": 0.9,
                "pause_ms": 320,
            },
        )
    )

    state = coordinator.get_session_state("session-1")
    assert state.user_audio.backchannel_opportunity == 0.85
    assert state.user_audio.barge_in_score == 0.9
    assert state.user_audio.pause_ms == 320


def test_process_event_calls_agents_and_returns_decisions() -> None:
    agent = ProposalAgent()
    coordinator = RuntimeCoordinator(agents=[agent])

    decisions = coordinator.process_event(
        Event(session_id="session-1", type=USER_SPEECH_END)
    )

    assert agent.observed == 1
    assert agent.proposed == 1
    assert len(decisions) == 1
    assert decisions[0]["decision"] == "play"
    assert decisions[0]["proposal_action"] == "SPEAK"


def test_process_events_handles_events_in_order() -> None:
    coordinator = RuntimeCoordinator()

    decisions = coordinator.process_events(
        [
            Event(session_id="session-1", type=USER_SPEECH_START),
            Event(
                session_id="session-1",
                type=ASR_PARTIAL,
                payload={"text": "我还在说"},
            ),
            Event(session_id="session-1", type=USER_SPEECH_END),
        ]
    )

    state = coordinator.get_session_state("session-1")
    assert state.user_audio.is_speaking is False
    assert state.asr.partial == "我还在说"
    assert len(state.events) == 3
    assert isinstance(decisions, list)
