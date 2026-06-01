from __future__ import annotations

import asyncio
import json

import pytest

from audio_input import EnergyVAD
from runtime.debug_session_runner import (
    DebugFrameSpec,
    DebugSessionRunner,
    flatten_decisions_from_route_summary,
    make_audio_frame,
    make_pcm,
    result_to_json_dict,
)


def test_make_pcm_generates_expected_energy_levels() -> None:
    vad = EnergyVAD()
    silence = make_pcm("silence", duration_ms=100)
    speech = make_pcm("speech", duration_ms=100)
    loud_speech = make_pcm("loud_speech", duration_ms=100)

    assert len(silence) > 0
    assert vad.calculate_rms(silence) == 0.0
    assert vad.calculate_rms(speech) > 0
    assert vad.calculate_rms(loud_speech) > vad.calculate_rms(speech)


def test_make_pcm_unknown_kind_raises() -> None:
    with pytest.raises(ValueError, match="unknown pcm kind"):
        make_pcm("noise", duration_ms=100)


def test_make_audio_frame_preserves_spec_metadata_and_duration() -> None:
    spec = DebugFrameSpec(
        timestamp_ms=1234,
        pcm_kind="speech",
        duration_ms=250,
        sample_rate=16000,
        metadata={"asr_text": "hello"},
    )

    frame = make_audio_frame(
        session_id="session-1",
        spec=spec,
        base_timestamp_ms=1000,
    )

    assert frame.timestamp_ms == 1234
    assert frame.samples_per_channel == 4000
    assert frame.duration_ms == 250.0
    assert frame.metadata == {"asr_text": "hello"}
    assert frame.source == "debug_runner"


def test_debug_session_runner_defaults_register_consumers() -> None:
    runner = DebugSessionRunner()

    assert runner.runtime_coordinator is not None
    assert runner.raw_audio_router is not None
    assert runner.backchannel_trigger is not None
    assert runner.asr_trigger is not None
    assert set(runner.raw_audio_router.get_consumer_names()) == {
        "asr",
        "backchannel",
    }


def test_flatten_decisions_from_route_summary_extracts_lists() -> None:
    route_summary = {
        "consumer_results": {
            "a": [{"decision": "play"}],
            "b": None,
            "c": {"decision": "duck"},
        }
    }

    assert flatten_decisions_from_route_summary(route_summary) == [
        {"decision": "play"},
        {"decision": "duck"},
    ]


def test_backchannel_scenario_produces_backchannel_decision() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("backchannel"))

    assert result.frames_processed == 3
    assert any(
        decision.get("proposal_action") == "BACKCHANNEL"
        or (
            decision.get("decision") == "play"
            and decision.get("lane") == "speech"
        )
        for decision in result.decisions
    )
    assert result.final_state["user_audio"]["backchannel_opportunity"] >= 0


def test_danger_scenario_sets_followup_metadata() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("danger"))

    assert result.final_state["asr"]["partial"] == "我准备直接删库"
    assert result.final_state["metadata"]["followup_needed"] is True
    assert any(
        decision.get("control_reason") == "dangerous_operation"
        or decision.get("control_action") == "INTERRUPT_USER"
        for decision in result.decisions
    )


def test_factual_scenario_outputs_obvious_error_decision() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("factual"))

    assert any(
        decision.get("control_reason") == "obvious_factual_error"
        for decision in result.decisions
    )


def test_bargein_scenario_stops_speech() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("bargein"))

    assert any(
        decision.get("control_action") == "STOP_SPEAKING"
        or decision.get("decision") == "stop"
        for decision in result.decisions
    )
    assert result.final_state["assistant"]["is_speaking"] is False


def test_normal_scenario_updates_final_asr_and_dialogue_decision() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("normal"))

    assert result.final_state["asr"]["final"] == "我想聊一下这个架构"
    assert any(
        decision.get("proposal_action") == "SPEAK"
        and decision.get("agent") == "dialogue"
        for decision in result.decisions
    )


def test_full_scenario_returns_json_serializable_summary() -> None:
    runner = DebugSessionRunner()

    result = runner.run_scenario_sync(runner.build_scenario("full"))
    json_dict = result_to_json_dict(result)

    assert result.frames_processed > 0
    assert result.decision_count > 0
    assert json.loads(json.dumps(json_dict, ensure_ascii=False))["scenario"] == "full"


def test_run_scenario_async() -> None:
    runner = DebugSessionRunner()

    async def run() -> int:
        result = await runner.run_scenario(runner.build_scenario("backchannel"))
        return result.frames_processed

    assert asyncio.run(run()) == 3
