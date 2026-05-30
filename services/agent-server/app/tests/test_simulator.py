from __future__ import annotations

from runtime import (
    run_simulation,
    simulate_backchannel_opportunity,
    simulate_dangerous_interrupt,
    simulate_normal_dialogue,
    simulate_sfx_trigger,
    simulate_user_barge_in,
)


def test_normal_dialogue_simulation_generates_dialogue_decision() -> None:
    result = run_simulation(simulate_normal_dialogue())

    assert result["event_count"] == 4
    assert any(
        decision.get("proposal_action") == "SPEAK"
        and decision.get("lane") == "speech"
        for decision in result["decisions"]
    )


def test_backchannel_simulation_generates_backchannel_play() -> None:
    result = run_simulation(simulate_backchannel_opportunity())

    assert any(
        decision.get("proposal_action") == "BACKCHANNEL"
        and decision.get("decision") == "play"
        and decision.get("lane") == "speech"
        for decision in result["decisions"]
    )


def test_user_barge_in_simulation_generates_stop_speaking() -> None:
    result = run_simulation(simulate_user_barge_in())

    assert any(
        decision.get("control_action") == "STOP_SPEAKING"
        and decision.get("decision") == "stop"
        for decision in result["decisions"]
    )


def test_dangerous_interrupt_simulation_generates_interrupt_user() -> None:
    result = run_simulation(simulate_dangerous_interrupt())

    assert any(
        decision.get("control_action") == "INTERRUPT_USER"
        and decision.get("control_reason") == "dangerous_operation"
        for decision in result["decisions"]
    )


def test_sfx_simulation_generates_sfx_lane_decision() -> None:
    result = run_simulation(simulate_sfx_trigger())

    assert any(
        decision.get("proposal_action") == "PLAY_SFX"
        and decision.get("lane") == "sfx"
        for decision in result["decisions"]
    )
