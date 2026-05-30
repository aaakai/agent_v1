from __future__ import annotations

from agents import SafetyPolicyAgent
from schemas import OutputProposal, SessionState


def proposal(
    lane: str,
    action: str,
    priority: int = 50,
    mixing: dict | None = None,
) -> OutputProposal:
    return OutputProposal(
        session_id="session-1",
        agent="test",
        lane=lane,
        action=action,
        priority=priority,
        mixing=mixing or {},
    )


def test_rejects_backchannel_when_assistant_is_speaking() -> None:
    agent = SafetyPolicyAgent()
    state = SessionState(session_id="session-1")
    state.assistant.is_speaking = True

    allowed, reason = agent.validate_proposal(
        proposal("speech", "BACKCHANNEL", priority=30),
        state,
    )

    assert allowed is False
    assert reason == "assistant_speaking_blocks_backchannel"


def test_rejects_low_priority_speech_when_user_is_speaking() -> None:
    agent = SafetyPolicyAgent()
    state = SessionState(session_id="session-1")
    state.user_audio.is_speaking = True

    allowed, reason = agent.validate_proposal(
        proposal("speech", "SPEAK", priority=50),
        state,
    )

    assert allowed is False
    assert reason == "user_speaking_blocks_low_priority_speech"


def test_rejects_loud_sfx() -> None:
    agent = SafetyPolicyAgent()
    state = SessionState(session_id="session-1")

    allowed, reason = agent.validate_proposal(
        proposal("sfx", "PLAY_SFX", priority=20, mixing={"gain": 0.9}),
        state,
    )

    assert allowed is False
    assert reason == "sfx_gain_too_high"


def test_allows_normal_proposal() -> None:
    agent = SafetyPolicyAgent()
    state = SessionState(session_id="session-1")

    allowed, reason = agent.validate_proposal(
        proposal("speech", "SPEAK", priority=95),
        state,
    )

    assert allowed is True
    assert reason == "allowed"
