from __future__ import annotations

from agents import MockInterruptAgent
from schemas import SessionState


def test_barge_in_outputs_stop_speaking() -> None:
    agent = MockInterruptAgent()
    state = SessionState(session_id="session-1")
    state.assistant.is_speaking = True
    state.user_audio.is_speaking = True
    state.user_audio.barge_in_score = 0.7

    result = agent.propose(state)

    assert len(result.control_actions) == 1
    action = result.control_actions[0]
    assert action.action == "STOP_SPEAKING"
    assert action.priority == 95
    assert action.reason == "user_barge_in"
    assert action.target == "speech_lane"
    assert action.payload == {
        "audio_triggered": True,
        "barge_in_score": 0.7,
    }


def test_dangerous_partial_outputs_interrupt_user() -> None:
    agent = MockInterruptAgent()
    state = SessionState(session_id="session-1")
    state.asr.partial = "准备删库跑路"

    result = agent.propose(state)

    action = result.control_actions[0]
    assert action.action == "INTERRUPT_USER"
    assert action.priority == 95
    assert action.reason == "dangerous_operation"
    assert action.target == "user"
    assert action.payload["semantic_triggered"] is True
    assert action.payload["interrupt_phrase"] == "等一下，先别操作。"
    assert action.payload["followup_needed"] is True
    assert action.payload["followup_policy"] == "dialogue_explain_if_user_pauses"
    assert action.payload["audio_context"]["is_speaking"] is False


def test_obvious_factual_error_outputs_interrupt_user() -> None:
    agent = MockInterruptAgent()
    state = SessionState(session_id="session-1")
    state.asr.partial = "一加一等于三"

    result = agent.propose(state)

    action = result.control_actions[0]
    assert action.action == "INTERRUPT_USER"
    assert action.priority == 85
    assert action.reason == "obvious_factual_error"
    assert action.payload["semantic_triggered"] is True
    assert action.payload["interrupt_phrase"] == "等一下，一加一是二。"
    assert action.payload["followup_needed"] is False


def test_normal_user_speech_outputs_allow_user_continue() -> None:
    agent = MockInterruptAgent()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True
    state.asr.partial = "我还在讲我的想法"

    result = agent.propose(state)

    action = result.control_actions[0]
    assert action.action == "ALLOW_USER_CONTINUE"
    assert action.priority == 0
    assert action.reason == "user_is_still_speaking"


def test_stop_speaking_takes_precedence_over_interrupt_user() -> None:
    agent = MockInterruptAgent()
    state = SessionState(session_id="session-1")
    state.assistant.is_speaking = True
    state.user_audio.is_speaking = True
    state.user_audio.barge_in_score = 0.9
    state.asr.partial = "我要删库"

    result = agent.propose(state)

    assert result.control_actions[0].action == "STOP_SPEAKING"
    assert result.control_actions[0].reason == "user_barge_in"
