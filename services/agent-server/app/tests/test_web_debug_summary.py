from __future__ import annotations

import json

from web_debug.api import run_debug_scenario
from web_debug.summary import (
    build_debug_summary,
    extract_user_input,
    infer_outcome,
    summarize_lanes,
)


def test_sfx_summary_has_readable_headline_and_lane_active() -> None:
    result = run_debug_scenario("sfx", with_player=True)
    summary = build_debug_summary(result)

    assert "音效" in summary["headline"] or "door_knock" in summary["headline"]
    assert summary["lanes"]["sfx"]["count"] > 0
    assert "door_knock" in summary["lanes"]["sfx"]["active"]
    assert any("PLAY_SFX" in action for action in summary["main_actions"])


def test_danger_summary_recognizes_dangerous_interrupt() -> None:
    result = run_debug_scenario("danger", with_player=True)
    summary = build_debug_summary(result)

    assert summary["headline"] == "检测到危险操作并触发 Interrupt"
    assert any("危险操作" in action for action in summary["main_actions"])
    assert any(
        item["action"] == "INTERRUPT_USER"
        for item in summary["key_decisions"]
    )
    assert "Interrupt 触发但没有 followup metadata" not in summary["warnings"]


def test_backchannel_summary_recognizes_backchannel_command() -> None:
    result = run_debug_scenario("backchannel", with_player=True)
    summary = build_debug_summary(result)

    assert summary["headline"] == "触发了 Backchannel 轻反馈"
    assert any("PLAY_BACKCHANNEL" in action for action in summary["main_actions"])
    assert summary["outcome"] == "assistant 轻声回应了一句 backchannel"


def test_bargein_summary_recognizes_stop_tts() -> None:
    result = run_debug_scenario("bargein", with_player=True)
    summary = build_debug_summary(result)

    assert summary["headline"] == "检测到用户打断，停止当前语音"
    assert any("STOP_TTS" in action for action in summary["main_actions"])
    assert summary["outcome"] == "assistant 停止了当前语音"


def test_summary_helpers_handle_missing_fields() -> None:
    summary = build_debug_summary({"scenario": "unknown"})

    assert summary["headline"] == "已完成场景运行"
    assert summary["user_input"] is None
    assert summary["warnings"] == ["没有产生 player_commands"]
    assert extract_user_input({}) is None
    assert summarize_lanes(None)["speech"]["status"] == "idle"
    assert infer_outcome([], None) == "没有产生播放器命令"


def test_summary_is_json_serializable() -> None:
    summary = build_debug_summary(run_debug_scenario("full", with_player=True))

    assert json.loads(json.dumps(summary, ensure_ascii=False))["scenario"] == "full"
