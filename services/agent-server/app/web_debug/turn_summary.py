from __future__ import annotations

from typing import Any


def build_turn_summary(result: dict[str, Any]) -> dict[str, Any]:
    debug_result = _dict(result.get("debug_result"))
    turn_status = _turn_status_from(debug_result)
    turn_detector = _dict(turn_status.get("turn_detector"))
    timeline = _timeline_from(turn_status, turn_detector)
    flush_count = _int(turn_status.get("flush_count"))
    last_flush_reason = _str_or_none(turn_status.get("last_flush_reason"))
    last_final_text = _last_final_text(result, debug_result, turn_status)
    silence_ms = _int_or_none(turn_detector.get("silence_ms"))
    silence_flush_ms = _int_or_none(turn_detector.get("silence_flush_ms"))
    status = _infer_turn_status(
        turn_detector=turn_detector,
        flush_count=flush_count,
        last_flush_reason=last_flush_reason,
        timeline=timeline,
    )
    has_turn = bool(
        timeline
        or flush_count
        or last_flush_reason
        or last_final_text
        or turn_detector.get("speech_started")
        or turn_detector.get("turn_open")
        or turn_detector.get("turn_final_emitted")
    )

    summary = {
        "has_turn": has_turn,
        "turn_status": status,
        "flush_count": flush_count,
        "last_flush_reason": last_flush_reason,
        "last_final_text": last_final_text,
        "silence_ms": silence_ms,
        "silence_flush_ms": silence_flush_ms,
        "timeline": timeline[-20:],
        "explanation": _build_explanation(
            has_turn=has_turn,
            status=status,
            flush_count=flush_count,
            last_flush_reason=last_flush_reason,
            last_final_text=last_final_text,
            silence_ms=silence_ms,
            silence_flush_ms=silence_flush_ms,
        ),
        "warnings": [],
    }
    summary["warnings"] = _collect_warnings(summary)
    return summary


def flush_reason_to_chinese(reason: str | None) -> str:
    mapping = {
        "silence": "静音达到阈值",
        "user_speech_end": "用户语音结束事件",
        "max_turn_duration": "单轮时长达到上限",
        "debug_force_turn_end": "调试强制结束",
        "manual": "手动触发",
    }
    if reason is None:
        return "未知原因"
    return mapping.get(reason, "未知原因")


def _turn_status_from(debug_result: dict[str, Any]) -> dict[str, Any]:
    direct = _dict(debug_result.get("turn_status"))
    if direct:
        return direct
    return _dict(_dict(debug_result.get("metadata")).get("asr_flush"))


def _timeline_from(
    turn_status: dict[str, Any],
    turn_detector: dict[str, Any],
) -> list[dict[str, Any]]:
    raw = turn_status.get("timeline")
    if not isinstance(raw, list):
        raw = turn_detector.get("timeline")
    return [item for item in _list(raw) if isinstance(item, dict)]


def _last_final_text(
    result: dict[str, Any],
    debug_result: dict[str, Any],
    turn_status: dict[str, Any],
) -> str | None:
    candidates: list[Any] = [
        _dict(_dict(turn_status.get("diagnostics")).get("status")).get("last_text"),
        _dict(turn_status.get("diagnostics")).get("last_final_text"),
        _dict(_dict(turn_status.get("asr_trigger")).get("diagnostics")).get("last_final_text"),
        _dict(_dict(debug_result.get("final_state")).get("asr")).get("final"),
        _dict(_dict(_dict(result.get("debug_result")).get("final_state")).get("asr")).get("final"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _infer_turn_status(
    turn_detector: dict[str, Any],
    flush_count: int,
    last_flush_reason: str | None,
    timeline: list[dict[str, Any]],
) -> str:
    if not turn_detector and not timeline and flush_count <= 0:
        return "unknown"
    if last_flush_reason == "user_speech_end":
        return "ended"
    if flush_count > 0 or turn_detector.get("turn_final_emitted") is True:
        return "flushed"
    if turn_detector.get("turn_open") is True:
        return "open"
    return "idle"


def _build_explanation(
    has_turn: bool,
    status: str,
    flush_count: int,
    last_flush_reason: str | None,
    last_final_text: str | None,
    silence_ms: int | None,
    silence_flush_ms: int | None,
) -> list[str]:
    if not has_turn:
        return ["本次结果里没有 turn boundary / ASR flush 调试信息。"]

    lines: list[str] = []
    if status == "open":
        lines.append("当前用户轮次仍处于打开状态，尚未触发 ASR flush。")
    elif status in {"flushed", "ended"}:
        lines.append(
            f"ASR flush 已触发 {flush_count} 次，最近原因是：{flush_reason_to_chinese(last_flush_reason)}。"
        )
    else:
        lines.append("TurnDetector 已记录状态，但当前没有打开的用户轮次。")

    if silence_ms is not None and silence_flush_ms is not None:
        lines.append(f"最近静音时长为 {silence_ms}ms，flush 阈值为 {silence_flush_ms}ms。")
    if last_final_text:
        lines.append(f"最近一次 turn-final ASR 文本是：“{last_final_text}”。")
    return lines


def _collect_warnings(summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if summary["has_turn"] and summary["flush_count"] > 0 and not summary.get("last_final_text"):
        warnings.append("ASR flush 已触发，但没有生成 ASR_FINAL 文本")
    if summary["turn_status"] == "open":
        warnings.append("用户轮次仍然打开，可能还在等待静音或 USER_SPEECH_END")
    return warnings


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
