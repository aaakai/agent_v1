from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schemas import Event

from .coordinator import RuntimeCoordinator


def load_jsonl_events(path: str | Path) -> list[Event]:
    events: list[Event] = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            events.append(Event.model_validate(json.loads(stripped)))
    return events


def replay_events(
    events: list[Event | dict[str, Any]],
    coordinator: RuntimeCoordinator | None = None,
) -> dict[str, Any]:
    active_coordinator = coordinator or RuntimeCoordinator()
    normalized_events = [
        event if isinstance(event, Event) else Event.model_validate(event)
        for event in events
    ]
    decisions = active_coordinator.process_events(normalized_events)
    session_ids = sorted({event.session_id for event in normalized_events})

    sessions: dict[str, Any] = {}
    for session_id in session_ids:
        state = active_coordinator.get_session_state(session_id)
        sessions[session_id] = {
            "event_count": len(state.events),
            "final_state": state.model_dump(mode="python"),
        }

    return {
        "event_count": len(normalized_events),
        "decision_count": len(decisions),
        "decisions": decisions,
        "sessions": sessions,
    }


def replay_jsonl(
    path: str | Path,
    coordinator: RuntimeCoordinator | None = None,
) -> dict[str, Any]:
    return replay_events(load_jsonl_events(path), coordinator=coordinator)
