from __future__ import annotations

from typing import Any


def build_narration(
    summary: dict[str, Any],
    result: dict[str, Any] | None = None,
) -> list[str]:
    safe_result = _dict(result)
    scenario = str(summary.get("scenario") or safe_result.get("scenario") or "unknown")
    command_types = extract_command_types(safe_result)
    user_input = _user_input(summary, safe_result)

    if scenario == "full":
        return _full_narration(command_types, user_input)
    if scenario == "sfx" or "PLAY_SFX" in command_types:
        return _sfx_narration(summary, safe_result, user_input)
    if scenario == "backchannel" or "PLAY_BACKCHANNEL" in command_types:
        return _backchannel_narration()
    if scenario == "danger" or _interrupt_reason(safe_result) == "dangerous_operation":
        return _danger_narration(user_input)
    if scenario == "factual" or _interrupt_reason(safe_result) == "obvious_factual_error":
        return _factual_narration()
    if scenario == "bargein" or "STOP_TTS" in command_types:
        return _bargein_narration()
    if scenario == "scene":
        return _scene_narration(safe_result)
    if scenario == "ambience" or "SET_AMBIENCE" in command_types:
        return _ambience_narration()
    if scenario == "normal" or "PLAY_TTS" in command_types:
        return _normal_narration()
    return [
        "本次 debug scenario 已完成运行。",
        "系统产生了若干事件、决策和播放器命令。",
        "可以查看下方的 Lane 状态和 Advanced JSON 进一步排查。",
    ]


def build_short_timeline(
    summary: dict[str, Any],
    result: dict[str, Any] | None = None,
) -> list[str]:
    safe_result = _dict(result)
    scenario = str(summary.get("scenario") or safe_result.get("scenario") or "unknown")
    command_types = extract_command_types(safe_result)
    user_input = _user_input(summary, safe_result)

    if scenario == "full":
        return _full_timeline(command_types, user_input)
    if scenario == "sfx" or "PLAY_SFX" in command_types:
        event = _first(extract_sfx_events(safe_result)) or "event_sfx"
        timeline = [
            f"用户输入：{user_input}" if user_input else None,
            "ASR_FINAL 更新文本",
            f"SFXPlannerAgent → {event}",
            f"SpatialAudioAgent → {extract_spatial_text(safe_result)}"
            if extract_spatial_text(safe_result)
            else None,
            "Orchestrator → 允许 SFX 播放",
            "Player → PLAY_SFX",
        ]
        return _present(timeline)

    if scenario == "backchannel" or "PLAY_BACKCHANNEL" in command_types:
        return [
            "检测到用户正在说话",
            "出现 200-500ms 短暂停顿",
            "BackchannelAgent → 轻反馈",
            "Orchestrator → Speech Lane 播放",
            "Player → PLAY_BACKCHANNEL",
        ]

    if scenario == "danger" or _interrupt_reason(safe_result) == "dangerous_operation":
        return [
            f"ASR_PARTIAL：{user_input or '危险操作'}",
            "InterruptAgent → dangerous_operation",
            "Orchestrator → interrupt control",
            "Session metadata → followup_needed",
            "DialogueAgent → 等待用户停顿后解释",
        ]

    if scenario == "factual" or _interrupt_reason(safe_result) == "obvious_factual_error":
        return [
            f"ASR_PARTIAL：{user_input or '明显事实错误'}",
            "InterruptAgent → obvious_factual_error",
            "Orchestrator → interrupt control",
            "Player → 短句纠错",
        ]

    if scenario == "bargein" or "STOP_TTS" in command_types:
        return [
            "Assistant 正在说话",
            "用户突然开口",
            "barge_in_score 达到阈值",
            "InterruptAgent → STOP_SPEAKING",
            "Player → STOP_TTS",
        ]

    if scenario == "scene":
        return ["SCENE_CHANGED", "RuntimeCoordinator → 更新 scene", "后续 SFX / ambience 使用新场景"]

    if scenario == "ambience" or "SET_AMBIENCE" in command_types:
        return ["读取 scene preset", "AmbienceController → SET_AMBIENCE", "Orchestrator → Ambience Lane", "Player → SET_AMBIENCE"]

    if scenario == "normal" or "PLAY_TTS" in command_types:
        return _present(
            [
                f"用户输入：{user_input}" if user_input else None,
                "ASR_FINAL 更新文本",
                "DialogueAgent → 普通回复",
                "Orchestrator → Speech Lane 播放",
                "Player → PLAY_TTS",
            ]
        )

    return ["scenario 运行完成", "查看 Lane 状态", "需要细节时展开 Advanced JSON"]


def extract_command_types(result: dict[str, Any]) -> list[str]:
    commands = _commands(result)
    return [
        str(command.get("type"))
        for command in commands
        if command.get("type") is not None
    ]


def extract_sfx_events(result: dict[str, Any]) -> list[str]:
    events: list[str] = []
    for command in _commands(result):
        payload = _dict(command.get("payload"))
        if command.get("type") == "PLAY_SFX":
            event = payload.get("event")
            if isinstance(event, str) and event:
                events.append(event)

    playback = _dict(result.get("playback_state"))
    sfx = _dict(playback.get("sfx"))
    for item in _list(sfx.get("active")):
        payload = _dict(_dict(item).get("payload"))
        event = payload.get("event") or _dict(item).get("event")
        if isinstance(event, str) and event:
            events.append(event)
    return _dedupe(events)


def extract_spatial_text(result: dict[str, Any]) -> str | None:
    spatial = _find_spatial(result)
    if not spatial:
        return None
    azimuth = _float_or_none(spatial.get("azimuth_deg"))
    distance = _float_or_none(spatial.get("distance_m"))
    parts = []
    azimuth_text = azimuth_to_chinese(azimuth)
    if azimuth_text:
        parts.append(azimuth_text)
    if distance is not None:
        parts.append(f"距离约 {distance:g} 米")
    return "，".join(parts) if parts else None


def azimuth_to_chinese(azimuth_deg: float | int | None) -> str | None:
    if azimuth_deg is None:
        return None
    degree = float(azimuth_deg)
    if -15 <= degree <= 15:
        return "正前方"
    if degree < -15:
        return f"左前方约 {abs(degree):g}°"
    return f"右前方约 {degree:g}°"


def _sfx_narration(
    summary: dict[str, Any],
    result: dict[str, Any],
    user_input: str | None,
) -> list[str]:
    event = _first(extract_sfx_events(result)) or "事件音效"
    spatial = extract_spatial_text(result)
    first = (
        f"本次场景模拟了用户提到“{user_input}”。"
        if user_input
        else "本次场景模拟了用户提到某个需要音效响应的事件。"
    )
    lines = [
        first,
        f"系统通过 ASR 得到用户文本后，SFXPlannerAgent 生成了 {event} 音效事件。",
    ]
    if spatial:
        lines.append(f"SpatialAudioAgent 为这个音效补充了空间位置，例如{spatial}。")
    else:
        lines.append("SpatialAudioAgent 会尝试为这个音效补充空间位置。")
    lines.append(f"最终播放器收到 PLAY_SFX 命令，SFX Lane 中出现了{_event_label(event)}。")
    return lines[:5]


def _backchannel_narration() -> list[str]:
    return [
        "本次场景模拟了用户说话过程中出现短暂停顿。",
        "音频特征提取器判断这个停顿适合轻反馈，BackchannelAgent 生成了 backchannel proposal。",
        "AudioOrchestrator 允许 Speech Lane 播放这次轻反馈。",
        "最终播放器收到 PLAY_BACKCHANNEL 命令，assistant 会轻声回应用户。",
    ]


def _danger_narration(user_input: str | None) -> list[str]:
    example = user_input or "删库"
    return [
        f"本次场景模拟了用户说出可能有风险的操作，例如“{example}”。",
        "ASR partial 命中了危险操作关键词，InterruptAgent 触发了 INTERRUPT_USER。",
        "系统先用短句打断用户，随后等待用户停顿后由 DialogueAgent 解释风险。",
        "这类 interrupt 依赖 ASR partial 的语义判断，会比纯音频判断稍慢，但更准确。",
    ]


def _factual_narration() -> list[str]:
    return [
        "本次场景模拟了用户说出明显事实错误。",
        "ASR partial 命中了“一加一等于三”这类错误表达。",
        "InterruptAgent 触发纠错型 interrupt，并准备短句提醒用户。",
        "这种场景属于语义型 interrupt，主要依赖 ASR partial。",
    ]


def _bargein_narration() -> list[str]:
    return [
        "本次场景模拟了 assistant 正在说话时用户突然插话。",
        "音频特征中的 barge_in_score 达到阈值，InterruptAgent 优先触发 STOP_SPEAKING。",
        "AudioOrchestrator 停止当前 Speech Lane 输出，让系统重新回到听用户说话的状态。",
        "这个动作是 audio-first，不需要等待 ASR partial。",
    ]


def _normal_narration() -> list[str]:
    return [
        "本次场景模拟了一次普通用户发言。",
        "ASR final 生成了稳定文本，DialogueAgent 基于这段文本生成回复。",
        "AudioOrchestrator 允许 Speech Lane 播放普通回复。",
        "最终播放器收到 PLAY_TTS 命令。",
    ]


def _scene_narration(result: dict[str, Any]) -> list[str]:
    scene_name = _dict(_dict(_dict(result.get("debug_result")).get("final_state")).get("scene")).get("name")
    return _present(
        [
            "本次场景模拟了一次场景切换。",
            f"RuntimeCoordinator 接收到 SCENE_CHANGED 后更新了当前 scene：{scene_name}。"
            if scene_name
            else "RuntimeCoordinator 接收到 SCENE_CHANGED 后更新了当前 scene。",
            "当前场景会影响后续的环境音、混响和 SFX 空间参数。",
        ]
    )


def _ambience_narration() -> list[str]:
    return [
        "本次场景模拟了环境音切换。",
        "AmbienceController 根据当前 scene 生成 SET_AMBIENCE 指令。",
        "AudioOrchestrator 将环境音放入 Ambience Lane。",
        "最终播放器会把该环境音作为低优先级背景持续播放。",
    ]


def _full_narration(command_types: list[str], user_input: str | None) -> list[str]:
    lines = ["本次场景模拟了一条综合链路。"]
    if user_input:
        lines.append(f"系统先通过 ASR 得到用户输入：“{user_input}”。")
    actions = []
    if "PLAY_BACKCHANNEL" in command_types:
        actions.append("轻反馈")
    if "PLAY_TTS" in command_types:
        actions.append("普通回复")
    if "PLAY_SFX" in command_types:
        actions.append("事件音效")
    if "STOP_TTS" in command_types:
        actions.append("用户打断")
    if actions:
        lines.append(f"链路中实际发生了{'、'.join(actions)}。")
    lines.append("AudioOrchestrator 负责把这些候选输出仲裁到对应播放 lane。")
    lines.append("最终播放器按 PlayerCommand 更新了本地 mock 播放状态。")
    return lines[:5]


def _full_timeline(command_types: list[str], user_input: str | None) -> list[str]:
    timeline = [f"用户输入：{user_input}" if user_input else "综合 scenario 开始"]
    if "PLAY_BACKCHANNEL" in command_types:
        timeline.append("BackchannelAgent → 轻反馈")
    if "PLAY_TTS" in command_types:
        timeline.append("DialogueAgent → 普通回复")
    if "PLAY_SFX" in command_types:
        timeline.append("SFXPlannerAgent → 事件音效")
    if "STOP_TTS" in command_types:
        timeline.append("InterruptAgent → STOP_SPEAKING")
    timeline.append("Player → 更新 mock playback state")
    return timeline[:7]


def _commands(result: dict[str, Any]) -> list[dict[str, Any]]:
    commands = result.get("player_commands")
    if not isinstance(commands, list):
        commands = _dict(result.get("debug_result")).get("player_commands")
    return [command for command in _list(commands) if isinstance(command, dict)]


def _user_input(summary: dict[str, Any], result: dict[str, Any]) -> str | None:
    value = summary.get("user_input")
    if isinstance(value, str) and value:
        return value
    debug_result = _dict(result.get("debug_result"))
    asr = _dict(_dict(debug_result.get("final_state")).get("asr"))
    value = asr.get("final") or asr.get("partial")
    return value if isinstance(value, str) and value else None


def _interrupt_reason(result: dict[str, Any]) -> str | None:
    metadata = _dict(_dict(_dict(result.get("debug_result")).get("final_state")).get("metadata"))
    reason = metadata.get("interrupt_reason")
    return reason if isinstance(reason, str) else None


def _find_spatial(result: dict[str, Any]) -> dict[str, Any] | None:
    for command in _commands(result):
        payload = _dict(command.get("payload"))
        spatial = _dict(payload.get("spatial"))
        if spatial:
            return spatial
    playback = _dict(result.get("playback_state"))
    for item in _list(_dict(playback.get("sfx")).get("active")):
        payload = _dict(_dict(item).get("payload"))
        spatial = _dict(payload.get("spatial") or _dict(item).get("spatial"))
        if spatial:
            return spatial
    return None


def _event_label(event: str) -> str:
    if event == "door_knock":
        return "门敲击音效"
    return event


def _first(values: list[str]) -> str | None:
    return values[0] if values else None


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _present(values: list[str | None]) -> list[str]:
    return [value for value in values if value]


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
