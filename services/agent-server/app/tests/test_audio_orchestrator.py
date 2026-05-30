from __future__ import annotations

from orchestrator import AudioOrchestrator
from schemas import ControlAction, Event, OutputProposal, SessionState
from schemas.event_types import CONTROL_ACTION, OUTPUT_PROPOSAL


def proposal(lane: str, action: str, agent: str = "dialogue") -> OutputProposal:
    return OutputProposal(
        session_id="session-1",
        agent=agent,
        lane=lane,
        action=action,
        text=f"{lane}-{action}",
    )


def test_orchestrator_dispatches_speech_sfx_and_ambience_proposals() -> None:
    orchestrator = AudioOrchestrator()
    state = SessionState(session_id="session-1")

    speech_decision = orchestrator.handle_output_proposal(
        proposal("speech", "SPEAK"),
        state=state,
        now_ms=1000,
    )
    sfx_decision = orchestrator.handle_output_proposal(
        proposal("sfx", "PLAY_SFX", agent="sfx"),
        state=state,
        now_ms=1100,
    )
    ambience_decision = orchestrator.handle_output_proposal(
        proposal("ambience", "SET_AMBIENCE", agent="scene"),
        state=state,
        now_ms=1200,
    )

    assert speech_decision["lane"] == "speech"
    assert speech_decision["decision"] == "play"
    assert sfx_decision["lane"] == "sfx"
    assert sfx_decision["decision"] == "play"
    assert sfx_decision["duck"] is True
    assert ambience_decision["lane"] == "ambience"
    assert ambience_decision["decision"] == "play"
    assert ambience_decision["duck"] is True


def test_stop_speaking_control_stops_speech_and_ducks_other_lanes() -> None:
    orchestrator = AudioOrchestrator()
    state = SessionState(session_id="session-1")
    orchestrator.handle_output_proposal(
        proposal("speech", "SPEAK"),
        state=state,
        now_ms=1000,
    )
    orchestrator.handle_output_proposal(
        proposal("sfx", "PLAY_SFX", agent="sfx"),
        state=state,
        now_ms=1100,
    )
    orchestrator.handle_output_proposal(
        proposal("ambience", "SET_AMBIENCE", agent="scene"),
        state=state,
        now_ms=1200,
    )
    action = ControlAction(
        session_id="session-1",
        agent="policy",
        action="STOP_SPEAKING",
        reason="user_barge_in",
    )

    decision = orchestrator.handle_control_action(action, state=state, now_ms=1300)

    assert decision["decision"] == "stop"
    assert decision["lane"] == "speech"
    assert state.assistant.is_speaking is False
    assert state.audio_runtime.speech_lane_busy is False
    assert [effect["lane"] for effect in decision["side_effects"]] == [
        "sfx",
        "ambience",
    ]
    assert all(effect["decision"] == "duck" for effect in decision["side_effects"])


def test_handle_event_processes_output_proposal() -> None:
    orchestrator = AudioOrchestrator()
    output = proposal("speech", "SPEAK")
    event = Event(
        session_id="session-1",
        type=OUTPUT_PROPOSAL,
        payload=output.model_dump(mode="python"),
    )

    decisions = orchestrator.handle_event(event)

    assert len(decisions) == 1
    assert decisions[0]["decision"] == "play"
    assert orchestrator.speech_lane.current is not None
    assert orchestrator.speech_lane.current.proposal_id == output.proposal_id


def test_handle_event_processes_control_action() -> None:
    orchestrator = AudioOrchestrator()
    state = orchestrator.session_state_manager.get_or_create("session-1")
    orchestrator.handle_output_proposal(
        proposal("speech", "SPEAK"),
        state=state,
        now_ms=1000,
    )
    action = ControlAction(
        session_id="session-1",
        agent="policy",
        action="STOP_SPEAKING",
    )
    event = Event(
        session_id="session-1",
        type=CONTROL_ACTION,
        payload=action.model_dump(mode="python"),
    )

    decisions = orchestrator.handle_event(event)

    assert len(decisions) == 1
    assert decisions[0]["decision"] == "stop"
    assert orchestrator.speech_lane.current is None


def test_state_snapshot_reports_lane_state() -> None:
    orchestrator = AudioOrchestrator()
    state = SessionState(session_id="session-1")
    orchestrator.handle_output_proposal(
        proposal("sfx", "PLAY_SFX", agent="sfx"),
        state=state,
        now_ms=1000,
    )

    snapshot = orchestrator.get_state_snapshot()

    assert snapshot["speech"]["queue_length"] == 0
    assert snapshot["sfx"]["active_count"] == 1
    assert snapshot["ambience"]["current"] is None
