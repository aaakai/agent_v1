from __future__ import annotations

import json

from web_debug.api import run_debug_scenario
from web_debug.narration import (
    azimuth_to_chinese,
    build_narration,
    build_short_timeline,
    extract_command_types,
    extract_sfx_events,
    extract_spatial_text,
)
from web_debug.summary import build_debug_summary


def test_sfx_narration_is_chinese_and_mentions_effect() -> None:
    result = run_debug_scenario("sfx", with_player=True)
    narration = result["simplified_summary"]["narration"]

    assert 3 <= len(narration) <= 5
    assert any("敲门" in line or "音效" in line for line in narration)
    assert any("PLAY_SFX" in line for line in narration)


def test_backchannel_narration_mentions_light_feedback() -> None:
    result = run_debug_scenario("backchannel", with_player=True)
    narration = result["simplified_summary"]["narration"]

    assert any("轻反馈" in line or "Backchannel" in line for line in narration)


def test_danger_narration_mentions_dangerous_operation() -> None:
    result = run_debug_scenario("danger", with_player=True)
    narration = result["simplified_summary"]["narration"]

    assert any("危险操作" in line or "删库" in line for line in narration)


def test_factual_narration_mentions_fact_error() -> None:
    result = run_debug_scenario("factual", with_player=True)
    narration = result["simplified_summary"]["narration"]

    assert any("事实错误" in line or "一加一" in line for line in narration)


def test_bargein_narration_mentions_interrupt() -> None:
    result = run_debug_scenario("bargein", with_player=True)
    narration = result["simplified_summary"]["narration"]

    assert any("打断" in line or "STOP_SPEAKING" in line for line in narration)


def test_normal_narration_mentions_reply() -> None:
    result = run_debug_scenario("normal", with_player=True)
    narration = result["simplified_summary"]["narration"]

    assert any("普通" in line or "回复" in line for line in narration)


def test_fallback_narration_and_short_timeline_do_not_crash() -> None:
    summary = {"scenario": "unknown"}

    narration = build_narration(summary, {})
    timeline = build_short_timeline(summary, {})

    assert len(narration) >= 1
    assert len(timeline) >= 1


def test_short_timeline_and_extractors_for_sfx() -> None:
    result = run_debug_scenario("sfx", with_player=True)
    summary = result["simplified_summary"]

    assert summary["short_timeline"]
    assert "PLAY_SFX" in extract_command_types(result)
    assert "door_knock" in extract_sfx_events(result)
    assert "距离约 2.5 米" in extract_spatial_text(result)


def test_azimuth_to_chinese() -> None:
    assert "左前方" in azimuth_to_chinese(-30)
    assert "右前方" in azimuth_to_chinese(30)
    assert "正前方" in azimuth_to_chinese(0)
    assert azimuth_to_chinese(None) is None


def test_build_debug_summary_includes_narration_and_is_json_friendly() -> None:
    result = run_debug_scenario("full", with_player=True)
    summary = build_debug_summary(result)

    assert summary["narration"]
    assert summary["short_timeline"]
    assert json.loads(json.dumps(summary, ensure_ascii=False))["scenario"] == "full"


def test_turn_final_narration_mentions_asr_flush() -> None:
    result = run_debug_scenario("turn_final", with_player=True)
    summary = result["simplified_summary"]

    assert any("ASR flush" in line or "ASR_FINAL" in line for line in summary["narration"])
    assert any("ASR flush" in line or "ASR_FINAL" in line for line in summary["short_timeline"])
