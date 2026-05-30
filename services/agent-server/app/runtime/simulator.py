from __future__ import annotations

from typing import Any

from schemas import Event
from schemas.event_types import (
    ASR_FINAL,
    ASR_PARTIAL,
    ASSISTANT_SPEECH_START,
    AUDIO_FEATURE_UPDATE,
    USER_SPEECH_END,
    USER_SPEECH_START,
)

from .coordinator import RuntimeCoordinator
from .replay import replay_events


def simulate_normal_dialogue(session_id: str = "sim_normal") -> list[Event]:
    return [
        Event(session_id=session_id, type=USER_SPEECH_START),
        Event(
            session_id=session_id,
            type=ASR_PARTIAL,
            payload={"text": "我想聊一下这个架构"},
        ),
        Event(
            session_id=session_id,
            type=ASR_FINAL,
            payload={"text": "我想聊一下这个架构"},
        ),
        Event(session_id=session_id, type=USER_SPEECH_END),
    ]


def simulate_backchannel_opportunity(
    session_id: str = "sim_backchannel",
) -> list[Event]:
    return [
        Event(session_id=session_id, type=USER_SPEECH_START),
        Event(
            session_id=session_id,
            type=AUDIO_FEATURE_UPDATE,
            payload={
                "backchannel_opportunity": 0.85,
                "pause_ms": 320,
                "energy": 0.5,
            },
        ),
    ]


def simulate_user_barge_in(session_id: str = "sim_bargein") -> list[Event]:
    return [
        Event(session_id=session_id, type=ASSISTANT_SPEECH_START),
        Event(session_id=session_id, type=USER_SPEECH_START),
        Event(
            session_id=session_id,
            type=AUDIO_FEATURE_UPDATE,
            payload={"barge_in_score": 0.9},
        ),
    ]


def simulate_dangerous_interrupt(session_id: str = "sim_danger") -> list[Event]:
    return [
        Event(session_id=session_id, type=USER_SPEECH_START),
        Event(
            session_id=session_id,
            type=ASR_PARTIAL,
            payload={"text": "我准备直接删库"},
        ),
    ]


def simulate_sfx_trigger(session_id: str = "sim_sfx") -> list[Event]:
    return [
        Event(session_id=session_id, type=USER_SPEECH_START),
        Event(
            session_id=session_id,
            type=ASR_FINAL,
            payload={"text": "突然有人敲门"},
        ),
        Event(session_id=session_id, type=USER_SPEECH_END),
    ]


def run_simulation(
    events: list[Event],
    coordinator: RuntimeCoordinator | None = None,
) -> dict[str, Any]:
    return replay_events(events, coordinator=coordinator)
