from __future__ import annotations

from orchestrator import SpeechLane
from schemas import ControlAction, OutputProposal, SessionState


def speech_proposal(
    action: str = "SPEAK",
    agent: str = "dialogue",
    priority: int | None = None,
) -> OutputProposal:
    kwargs = {
        "session_id": "session-1",
        "agent": agent,
        "lane": "speech",
        "action": action,
        "text": "hello",
    }
    if priority is not None:
        kwargs["priority"] = priority
    return OutputProposal(**kwargs)


def test_dialogue_queues_while_user_is_speaking() -> None:
    lane = SpeechLane()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True
    proposal = speech_proposal()

    decision = lane.apply_proposal(proposal, state, now_ms=1000)

    assert decision["decision"] == "queue"
    assert decision["reason"] == "user_speaking_queue_dialogue"
    assert lane.queue == [proposal]
    assert lane.current is None


def test_dialogue_can_play_when_user_is_not_speaking() -> None:
    lane = SpeechLane()
    state = SessionState(session_id="session-1")
    proposal = speech_proposal()

    decision = lane.apply_proposal(proposal, state, now_ms=1000)

    assert decision["decision"] == "play"
    assert lane.current == proposal
    assert state.assistant.is_speaking is True
    assert state.audio_runtime.speech_lane_busy is True


def test_backchannel_can_play_when_user_speaks_and_speech_is_idle() -> None:
    lane = SpeechLane()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True
    proposal = speech_proposal(action="BACKCHANNEL", agent="backchannel")

    decision = lane.apply_proposal(proposal, state, now_ms=1000)

    assert decision["decision"] == "play"
    assert lane.current == proposal
    assert lane.last_backchannel_at_ms == 1000


def test_backchannel_rejects_while_dialogue_is_playing() -> None:
    lane = SpeechLane()
    state = SessionState(session_id="session-1")
    dialogue = speech_proposal()
    lane.apply_proposal(dialogue, state, now_ms=1000)
    state.user_audio.is_speaking = True
    backchannel = speech_proposal(action="BACKCHANNEL", agent="backchannel")

    decision = lane.apply_proposal(backchannel, state, now_ms=1200)

    assert decision["decision"] == "reject"
    assert decision["reason"] == "speech_lane_busy"


def test_backchannel_cooldown_rejects_second_backchannel() -> None:
    lane = SpeechLane()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True
    first = speech_proposal(action="BACKCHANNEL", agent="backchannel")
    second = speech_proposal(action="BACKCHANNEL", agent="backchannel")
    lane.apply_proposal(first, state, now_ms=1000)
    lane.apply_control(
        ControlAction(
            session_id="session-1",
            agent="system",
            action="STOP_SPEAKING",
        ),
        state,
        now_ms=1100,
    )

    decision = lane.apply_proposal(second, state, now_ms=2000)

    assert decision["decision"] == "reject"
    assert decision["reason"] == "backchannel_cooldown"


def test_interrupt_priority_preempts_current_dialogue() -> None:
    lane = SpeechLane()
    state = SessionState(session_id="session-1")
    dialogue = speech_proposal()
    interrupt = speech_proposal(agent="interrupt", priority=95)
    lane.apply_proposal(dialogue, state, now_ms=1000)

    decision = lane.apply_proposal(interrupt, state, now_ms=1200)

    assert decision["decision"] == "preempt"
    assert decision["preempted"]["proposal_id"] == dialogue.proposal_id
    assert lane.current == interrupt


def test_stop_speaking_stops_current_speech() -> None:
    lane = SpeechLane()
    state = SessionState(session_id="session-1")
    dialogue = speech_proposal()
    lane.apply_proposal(dialogue, state, now_ms=1000)
    action = ControlAction(
        session_id="session-1",
        agent="policy",
        action="STOP_SPEAKING",
    )

    decision = lane.apply_control(action, state, now_ms=1500)

    assert decision["decision"] == "stop"
    assert decision["stopped"]["proposal_id"] == dialogue.proposal_id
    assert lane.current is None
    assert state.assistant.is_speaking is False
    assert state.audio_runtime.speech_lane_busy is False
