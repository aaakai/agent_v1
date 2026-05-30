from __future__ import annotations

from orchestrator import PriorityPolicy


def test_default_priorities_for_control_and_output_actions() -> None:
    policy = PriorityPolicy()

    assert policy.get_default_priority("STOP_SPEAKING") == 95
    assert policy.get_default_priority("INTERRUPT_USER") == 95
    assert policy.get_default_priority("BACKCHANNEL") == 30
    assert policy.get_default_priority("PLAY_SFX") == 20
    assert policy.get_default_priority("SET_AMBIENCE") == 10
    assert policy.get_default_priority("SPEAK", agent="dialogue") == 50
    assert policy.get_default_priority("UNKNOWN") == 50


def test_priority_comparison_and_ducking_policy() -> None:
    policy = PriorityPolicy()

    assert policy.is_higher_priority(95, 50) is True
    assert policy.is_higher_priority(50, 95) is False
    assert policy.should_duck_under_speech("sfx") is True
    assert policy.should_duck_under_speech("ambience") is True
    assert policy.should_duck_under_speech("speech") is False
