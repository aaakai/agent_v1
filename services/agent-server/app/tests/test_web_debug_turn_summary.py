from __future__ import annotations

import json

from web_debug.api import run_debug_scenario
from web_debug.turn_summary import build_turn_summary, flush_reason_to_chinese


def test_flush_reason_to_chinese_known_and_unknown() -> None:
    assert flush_reason_to_chinese("silence") == "静音达到阈值"
    assert flush_reason_to_chinese("user_speech_end") == "用户语音结束事件"
    assert flush_reason_to_chinese("max_turn_duration") == "单轮时长达到上限"
    assert flush_reason_to_chinese("debug_force_turn_end") == "调试强制结束"
    assert flush_reason_to_chinese("manual") == "手动触发"
    assert flush_reason_to_chinese(None) == "未知原因"
    assert flush_reason_to_chinese("other") == "未知原因"


def test_build_turn_summary_for_turn_final() -> None:
    payload = run_debug_scenario("turn_final", with_player=True)
    summary = build_turn_summary(payload)

    assert summary["has_turn"] is True
    assert summary["turn_status"] == "flushed"
    assert summary["flush_count"] >= 1
    assert summary["last_flush_reason"] == "silence"
    assert summary["last_final_text"] == "我想测试一下"
    assert summary["silence_ms"] == 800
    assert summary["silence_flush_ms"] == 700
    assert any(item["type"] == "flush" for item in summary["timeline"])
    assert any("ASR flush" in line for line in summary["explanation"])
    json.dumps(summary, ensure_ascii=False)


def test_build_turn_summary_for_short_utterance() -> None:
    payload = run_debug_scenario("short_utterance", with_player=False)
    summary = payload["simplified_summary"]["turn_summary"]

    assert summary["has_turn"] is True
    assert summary["turn_status"] == "ended"
    assert summary["last_flush_reason"] == "user_speech_end"
    assert summary["last_final_text"] == "短句测试"


def test_build_turn_summary_handles_missing_fields() -> None:
    summary = build_turn_summary({"scenario": "unknown"})

    assert summary["has_turn"] is False
    assert summary["turn_status"] == "unknown"
    assert summary["timeline"] == []
