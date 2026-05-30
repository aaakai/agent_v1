from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas import (
    ControlAction,
    Event,
    OutputProposal,
    SessionState,
)
from schemas.event_types import CONTROL_ACTION, OUTPUT_PROPOSAL, USER_SPEECH_START


def test_event_creation_generates_id_and_timestamp() -> None:
    event = Event(session_id="session-1", type=USER_SPEECH_START)

    assert event.event_id
    assert event.timestamp_ms > 0
    assert event.type == USER_SPEECH_START
    assert event.session_id == "session-1"
    assert event.payload == {}


def test_event_requires_type_and_session_id() -> None:
    with pytest.raises(ValidationError):
        Event(type=USER_SPEECH_START)

    with pytest.raises(ValidationError):
        Event(session_id="session-1")

    with pytest.raises(ValidationError):
        Event(session_id="", type=USER_SPEECH_START)

    with pytest.raises(ValidationError):
        Event(session_id="session-1", type="")


def test_output_proposal_creation_defaults_and_fields() -> None:
    proposal = OutputProposal(
        session_id="session-1",
        agent="dialog-agent",
        lane="speech",
        action="SPEAK",
        text="Hello",
    )

    assert proposal.proposal_id
    assert proposal.priority == 50
    assert proposal.session_id == "session-1"
    assert proposal.agent == "dialog-agent"
    assert proposal.lane == "speech"
    assert proposal.action == "SPEAK"
    assert proposal.text == "Hello"
    assert proposal.timing == {}
    assert OUTPUT_PROPOSAL == "OUTPUT_PROPOSAL"


def test_control_action_creation_defaults_and_fields() -> None:
    action = ControlAction(
        session_id="session-1",
        agent="policy-agent",
        action="STOP_SPEAKING",
        reason="user barge-in",
    )

    assert action.action_id
    assert action.action == "STOP_SPEAKING"
    assert action.reason == "user barge-in"
    assert action.priority == 50
    assert action.payload == {}
    assert CONTROL_ACTION == "CONTROL_ACTION"


def test_session_state_initializes_child_state_defaults() -> None:
    state = SessionState(session_id="session-1")

    assert state.session_id == "session-1"
    assert state.turn_id is None
    assert state.user_audio.is_speaking is False
    assert state.user_audio.pause_ms == 0
    assert state.user_audio.backchannel_opportunity == 0.0
    assert state.user_audio.barge_in_score == 0.0
    assert state.asr.stability == 0.0
    assert state.assistant.is_speaking is False
    assert state.assistant.speech_lane_busy is False
    assert state.scene.name == "default"
    assert state.audio_runtime.speech_lane_busy is False
    assert state.audio_runtime.sfx_playing == []
    assert state.events == []
    assert state.metadata == {}
