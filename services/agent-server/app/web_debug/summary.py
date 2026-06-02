from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from web_debug.narration import build_narration, build_short_timeline


class DebugSummary(BaseModel):
    scenario: str
    headline: str
    user_input: str | None = None
    outcome: str
    narration: list[str] = Field(default_factory=list)
    short_timeline: list[str] = Field(default_factory=list)
    main_actions: list[str] = Field(default_factory=list)
    lanes: dict[str, Any] = Field(default_factory=dict)
    key_decisions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    counters: dict[str, int] = Field(default_factory=dict)
    raw_refs: dict[str, Any] = Field(default_factory=dict)


def build_debug_summary(result: dict[str, Any]) -> dict[str, Any]:
    debug_result = _dict(result.get("debug_result"))
    player_commands = _list(result.get("player_commands") or debug_result.get("player_commands"))
    playback_state = result.get("playback_state")
    if not isinstance(playback_state, dict):
        playback_state = None

    scenario = str(result.get("scenario") or debug_result.get("scenario") or "unknown")
    user_input = extract_user_input(debug_result)
    lanes = summarize_lanes(playback_state)
    counters = {
        "frames_processed": _int(debug_result.get("frames_processed")),
        "event_count": _int(debug_result.get("event_count")),
        "decision_count": _int(debug_result.get("decision_count")),
        "player_command_count": len(player_commands),
        "commands_applied": _int(result.get("commands_applied")),
    }
    key_decisions = extract_key_decisions(debug_result, player_commands, playback_state)
    summary = DebugSummary(
        scenario=scenario,
        headline=infer_headline(scenario, result),
        user_input=user_input,
        outcome=infer_outcome(player_commands, playback_state),
        main_actions=_main_actions_for(
            scenario=scenario,
            user_input=user_input,
            result=result,
            player_commands=player_commands,
            key_decisions=key_decisions,
        ),
        lanes=lanes,
        key_decisions=key_decisions,
        counters=counters,
        raw_refs={
            "session_id": debug_result.get("session_id"),
            "decision_count": counters["decision_count"],
        },
    )
    payload = summary.model_dump(mode="python")
    payload["warnings"] = collect_warnings(result, payload)
    try:
        payload["narration"] = build_narration(payload, result)
    except Exception as exc:  # noqa: BLE001 - debug summary should not break the API.
        payload["narration"] = ["本次 debug scenario 已完成运行。"]
        payload["warnings"].append(f"narration 生成失败：{exc}")
    try:
        payload["short_timeline"] = build_short_timeline(payload, result)
    except Exception as exc:  # noqa: BLE001 - debug summary should not break the API.
        payload["short_timeline"] = ["scenario 运行完成"]
        payload["warnings"].append(f"short_timeline 生成失败：{exc}")
    return _json_roundtrip(payload)


def extract_user_input(debug_result: dict[str, Any]) -> str | None:
    final_state = _dict(debug_result.get("final_state"))
    asr = _dict(final_state.get("asr"))
    text = asr.get("final") or asr.get("partial")
    if isinstance(text, str) and text.strip():
        return text

    for decision in _list(debug_result.get("decisions")):
        payload_text = _find_first_string(
            decision,
            keys=("asr_text", "text", "transcript"),
        )
        if payload_text:
            return payload_text
    return None


def summarize_lanes(playback_state: dict[str, Any] | None) -> dict[str, Any]:
    if not playback_state:
        return {
            "speech": {"status": "idle", "current": None, "queue_count": 0},
            "sfx": {"status": "idle", "active": [], "count": 0},
            "ambience": {"status": "none", "current": None},
        }

    speech = _dict(playback_state.get("speech"))
    sfx = _dict(playback_state.get("sfx"))
    ambience = _dict(playback_state.get("ambience"))
    speech_current = _dict_or_none(speech.get("current"))
    sfx_active = [_sfx_label(item) for item in _list(sfx.get("active"))]
    ambience_current = _dict_or_none(ambience.get("current"))

    return {
        "speech": {
            "status": _speech_status(speech),
            "current": _speech_label(speech_current),
            "queue_count": len(_list(speech.get("queue"))),
        },
        "sfx": {
            "status": "ducked" if sfx.get("ducked") else ("active" if sfx_active else "idle"),
            "active": sfx_active,
            "count": len(sfx_active),
        },
        "ambience": {
            "status": _ambience_status(ambience),
            "current": _ambience_label(ambience_current),
        },
    }


def extract_key_decisions(
    debug_result: dict[str, Any],
    player_commands: list[dict[str, Any]],
    playback_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    user_input = extract_user_input(debug_result)
    if user_input:
        steps.append(_step("ASR", "识别用户输入", f"ASR 识别到：{user_input}"))

    for decision in _important_decisions(_list(debug_result.get("decisions"))):
        source = _decision_source(decision)
        action = str(
            decision.get("proposal_action")
            or decision.get("control_action")
            or decision.get("decision")
            or "decision"
        )
        detail = _decision_detail(decision)
        steps.append(_step(source, action, detail))

    for command in player_commands:
        command_type = str(command.get("type", "PlayerCommand"))
        steps.append(_step("Player", command_type, f"PlayerCommand 输出 {command_type}"))

    if playback_state and not steps:
        steps.append(_step("Player", "snapshot", "播放器状态已更新"))

    return [
        {**item, "step": index + 1}
        for index, item in enumerate(_dedupe_steps(steps)[:12])
    ]


def infer_headline(scenario: str, result: dict[str, Any]) -> str:
    debug_result = _dict(result.get("debug_result"))
    final_state = _dict(debug_result.get("final_state"))
    scene = _dict(final_state.get("scene"))
    commands = _list(result.get("player_commands") or debug_result.get("player_commands"))
    command_types = {command.get("type") for command in commands}

    if scenario == "backchannel":
        return "触发了 Backchannel 轻反馈"
    if scenario == "danger":
        return "检测到危险操作并触发 Interrupt"
    if scenario == "factual":
        return "检测到明显事实错误并触发 Interrupt"
    if scenario == "bargein":
        return "检测到用户打断，停止当前语音"
    if scenario == "sfx":
        event = _first_command_event(commands)
        return "触发了门敲击音效" if event == "door_knock" else "触发了事件音效"
    if scenario == "scene":
        name = scene.get("name")
        return f"切换到 {name} 场景" if name else "切换了场景"
    if scenario == "ambience":
        return "切换了环境音"
    if scenario == "normal":
        return "完成一次普通对话回复"
    if scenario == "full":
        if "STOP_TTS" in command_types:
            return "完成综合链路运行，并处理了用户打断"
        return "完成综合链路运行"
    return "已完成场景运行"


def infer_outcome(
    player_commands: list[dict[str, Any]],
    playback_state: dict[str, Any] | None,
) -> str:
    command_types = [command.get("type") for command in player_commands]
    if "STOP_TTS" in command_types:
        return "assistant 停止了当前语音"
    if "PLAY_BACKCHANNEL" in command_types:
        return "assistant 轻声回应了一句 backchannel"
    if "SET_AMBIENCE" in command_types:
        return "切换了环境音"
    if "PLAY_SFX" in command_types:
        return "播放了事件音效"
    if "PLAY_TTS" in command_types:
        return "assistant 生成了语音回复"
    if playback_state:
        return "播放器状态已更新，但没有新的播放命令"
    return "没有产生播放器命令"


def collect_warnings(result: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    debug_result = _dict(result.get("debug_result"))
    commands = _list(result.get("player_commands") or debug_result.get("player_commands"))
    playback_state = result.get("playback_state")
    final_state = _dict(debug_result.get("final_state"))
    metadata = _dict(final_state.get("metadata"))

    if not commands:
        warnings.append("没有产生 player_commands")
    if result.get("with_player") is True and not isinstance(playback_state, dict):
        warnings.append("scenario 运行成功，但没有 playback_state")
    for command in commands:
        if command.get("type") == "PLAY_SFX":
            payload = _dict(command.get("payload"))
            if not payload.get("spatial"):
                warnings.append("SFX command 缺少 spatial metadata")
                break
    if summary.get("scenario") == "danger" and metadata.get("followup_needed") is not True:
        warnings.append("Interrupt 触发但没有 followup metadata")
    return warnings


def _main_actions_for(
    scenario: str,
    user_input: str | None,
    result: dict[str, Any],
    player_commands: list[dict[str, Any]],
    key_decisions: list[dict[str, Any]],
) -> list[str]:
    command_types = [str(command.get("type")) for command in player_commands]
    debug_result = _dict(result.get("debug_result"))
    final_state = _dict(debug_result.get("final_state"))
    metadata = _dict(final_state.get("metadata"))

    if scenario == "backchannel":
        return _present(
            [
                "检测到用户说话中的短暂停顿",
                "BackchannelAgent 生成轻反馈",
                _command_action("PLAY_BACKCHANNEL", command_types),
            ]
        )
    if scenario == "danger":
        return _present(
            [
                "ASR partial 命中危险操作",
                "InterruptAgent 触发 INTERRUPT_USER",
                (
                    "等待用户停顿后由 DialogueAgent 解释风险"
                    if metadata.get("followup_needed") is True
                    else None
                ),
            ]
        )
    if scenario == "factual":
        return ["ASR partial 命中明显事实错误", "InterruptAgent 触发纠错"]
    if scenario == "bargein":
        return _present(
            [
                "检测到用户在 assistant 说话时开口",
                "InterruptAgent 触发 STOP_SPEAKING",
                _command_action("STOP_TTS", command_types),
            ]
        )
    if scenario == "sfx":
        event = _first_command_event(player_commands) or "event_sfx"
        spatial = _has_sfx_spatial(player_commands)
        return _present(
            [
                f"ASR 识别到：{user_input}" if user_input else None,
                f"SFXPlannerAgent 生成 {event}",
                "SpatialAudioAgent 添加空间位置" if spatial else None,
                "AudioOrchestrator 允许 SFX lane 播放",
                _command_action("PLAY_SFX", command_types),
            ]
        )
    if scenario == "scene":
        return ["SCENE_CHANGED 更新场景", "当前 ambience/reverb 已更新"]
    if scenario == "ambience":
        return _present(
            [
                "AmbienceController 生成 SET_AMBIENCE",
                _command_action("SET_AMBIENCE", command_types),
            ]
        )
    if scenario == "normal":
        return _present(
            [
                "ASR final 生成用户输入" if user_input else None,
                "DialogueAgent 生成回复",
                _command_action("PLAY_TTS", command_types),
            ]
        )
    if scenario == "full":
        return [
            step["detail"]
            for step in key_decisions
            if isinstance(step.get("detail"), str)
        ][:6]
    return [
        step["detail"]
        for step in key_decisions
        if isinstance(step.get("detail"), str)
    ][:6]


def _important_decisions(decisions: list[Any]) -> list[dict[str, Any]]:
    important: list[dict[str, Any]] = []
    for item in decisions:
        decision = _dict(item)
        action = decision.get("proposal_action") or decision.get("control_action")
        reason = decision.get("control_reason") or decision.get("reason")
        lane = decision.get("lane")
        if action in {
            "BACKCHANNEL",
            "SPEAK",
            "PLAY_SFX",
            "SET_AMBIENCE",
            "STOP_SPEAKING",
            "INTERRUPT_USER",
        }:
            important.append(decision)
        elif reason in {
            "dangerous_operation",
            "obvious_factual_error",
            "user_barge_in",
        }:
            important.append(decision)
        elif decision.get("decision") in {"play", "stop", "replace"} and lane in {
            "speech",
            "sfx",
            "ambience",
        }:
            important.append(decision)
    return important


def _decision_source(decision: dict[str, Any]) -> str:
    agent = str(decision.get("agent") or "")
    action = decision.get("proposal_action") or decision.get("control_action")
    if agent == "backchannel":
        return "BackchannelAgent"
    if agent == "interrupt":
        return "InterruptAgent"
    if agent == "sfx_planner":
        return "SFXPlannerAgent"
    if agent == "ambience_controller":
        return "AmbienceController"
    if agent == "dialogue":
        return "DialogueAgent"
    if action:
        return "AudioOrchestrator"
    return "Runtime"


def _decision_detail(decision: dict[str, Any]) -> str:
    action = decision.get("proposal_action") or decision.get("control_action")
    reason = decision.get("control_reason") or decision.get("reason")
    lane = decision.get("lane")
    proposal = _dict(decision.get("proposal"))
    metadata = _dict(proposal.get("metadata"))
    if action == "PLAY_SFX":
        event = metadata.get("event") or decision.get("event") or "event_sfx"
        return f"SFXPlannerAgent 生成 {event}，AudioOrchestrator 允许 {lane} lane 播放"
    if action == "BACKCHANNEL":
        return "BackchannelAgent 生成轻反馈，AudioOrchestrator 允许 speech lane 播放"
    if action == "SPEAK":
        return "DialogueAgent 生成语音回复，AudioOrchestrator 允许 speech lane 播放"
    if action == "SET_AMBIENCE":
        asset = metadata.get("asset") or metadata.get("ambience") or "ambience"
        return f"AmbienceController 生成 {asset} 环境音"
    if action == "STOP_SPEAKING":
        return "InterruptAgent 触发 STOP_SPEAKING，停止当前语音"
    if action == "INTERRUPT_USER":
        return f"InterruptAgent 触发 INTERRUPT_USER：{reason or 'interrupt'}"
    return f"{decision.get('decision', 'decision')} on {lane or 'runtime'}"


def _speech_status(speech: dict[str, Any]) -> str:
    if speech.get("ducked"):
        return "ducked"
    if speech.get("stopped"):
        return "stopped"
    if speech.get("current"):
        return "playing"
    return "idle"


def _ambience_status(ambience: dict[str, Any]) -> str:
    if ambience.get("ducked"):
        return "ducked"
    if ambience.get("stopped"):
        return "stopped"
    if ambience.get("current"):
        return "active"
    return "none"


def _speech_label(current: dict[str, Any] | None) -> str | None:
    if not current:
        return None
    payload = _dict(current.get("payload"))
    text = payload.get("text")
    if isinstance(text, str) and text:
        return text
    return str(current.get("type") or "speech")


def _sfx_label(item: Any) -> str:
    payload = _dict(_dict(item).get("payload"))
    return str(payload.get("event") or _dict(item).get("event") or "sfx")


def _ambience_label(current: dict[str, Any] | None) -> str | None:
    if not current:
        return None
    payload = _dict(current.get("payload"))
    return str(
        payload.get("asset")
        or payload.get("ambience")
        or payload.get("scene")
        or current.get("type")
        or "ambience"
    )


def _first_command_event(commands: list[dict[str, Any]]) -> str | None:
    for command in commands:
        payload = _dict(command.get("payload"))
        event = payload.get("event")
        if isinstance(event, str) and event:
            return event
    return None


def _has_sfx_spatial(commands: list[dict[str, Any]]) -> bool:
    return any(
        command.get("type") == "PLAY_SFX" and bool(_dict(command.get("payload")).get("spatial"))
        for command in commands
    )


def _command_action(command_type: str, command_types: list[str]) -> str | None:
    if command_type in command_types:
        return f"PlayerCommand 输出 {command_type}"
    return None


def _find_first_string(value: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(value, dict):
        for key in keys:
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item
        for item in value.values():
            found = _find_first_string(item, keys)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_first_string(item, keys)
            if found:
                return found
    return None


def _step(source: str, action: str, detail: str) -> dict[str, Any]:
    return {"source": source, "action": action, "detail": detail}


def _dedupe_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    output: list[dict[str, Any]] = []
    for step in steps:
        key = (
            str(step.get("source")),
            str(step.get("action")),
            str(step.get("detail")),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(step)
    return output


def _present(values: list[str | None]) -> list[str]:
    return [value for value in values if value]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _json_roundtrip(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))
