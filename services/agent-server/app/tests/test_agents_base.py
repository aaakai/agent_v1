from __future__ import annotations

from agents import BaseAgent
from schemas import Event, SessionState


def test_base_agent_observe_and_propose_return_empty_results() -> None:
    agent = BaseAgent(name="base")
    state = SessionState(session_id="session-1")
    event = Event(session_id="session-1", type="TEST_EVENT")

    observed = agent.observe(event, state)
    proposed = agent.propose(state)

    assert observed.proposals == []
    assert observed.control_actions == []
    assert observed.state_updates == []
    assert observed.metadata == {}
    assert proposed.proposals == []
    assert proposed.control_actions == []
    assert proposed.state_updates == []
    assert proposed.metadata == {}


def test_base_agent_make_metadata_includes_agent_name() -> None:
    agent = BaseAgent(name="base")

    assert agent.make_metadata(trigger="unit_test") == {
        "agent": "base",
        "trigger": "unit_test",
    }
