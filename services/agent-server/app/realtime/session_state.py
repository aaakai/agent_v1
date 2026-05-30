from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from schemas import Event, SessionState


PATCHABLE_FIELDS = {
    "user_audio",
    "asr",
    "assistant",
    "scene",
    "audio_runtime",
    "metadata",
    "turn_id",
}


def _recursive_merge(
    current: dict[str, Any],
    patch: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(current)
    for key, value in patch.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            merged[key] = _recursive_merge(existing, value)
        else:
            merged[key] = value
    return merged


class SessionStateManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def update(self, session_id: str, patch: dict[str, Any]) -> SessionState:
        if not isinstance(patch, dict):
            raise TypeError("patch must be a dict")

        state = self.get_or_create(session_id)
        state_data = state.model_dump(mode="python")
        for key, value in patch.items():
            if key not in PATCHABLE_FIELDS:
                continue
            existing = state_data.get(key)
            if isinstance(existing, dict) and isinstance(value, Mapping):
                state_data[key] = _recursive_merge(existing, value)
            else:
                state_data[key] = value

        updated = SessionState.model_validate(state_data)
        self._sessions[session_id] = updated
        return updated

    def append_event(self, session_id: str, event: Event) -> None:
        state = self.get_or_create(session_id)
        state.events.append(event)

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
