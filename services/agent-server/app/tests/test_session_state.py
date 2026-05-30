from __future__ import annotations

from realtime import SessionStateManager
from schemas import Event
from schemas.event_types import ASR_PARTIAL


def test_get_or_create_creates_session() -> None:
    manager = SessionStateManager()

    state = manager.get_or_create("session-1")

    assert state.session_id == "session-1"
    assert manager.get("session-1") is state


def test_update_applies_nested_state_patch() -> None:
    manager = SessionStateManager()

    state = manager.update(
        "session-1",
        {
            "user_audio": {"is_speaking": True},
            "asr": {"partial": "hello wor"},
            "scene": {"name": "kitchen"},
        },
    )

    assert state.user_audio.is_speaking is True
    assert state.asr.partial == "hello wor"
    assert state.scene.name == "kitchen"


def test_update_recursively_merges_metadata() -> None:
    manager = SessionStateManager()
    manager.update("session-1", {"metadata": {"client": {"version": 1}}})

    state = manager.update(
        "session-1",
        {"metadata": {"client": {"platform": "ios"}}},
    )

    assert state.metadata == {"client": {"version": 1, "platform": "ios"}}


def test_append_event_adds_event_to_session() -> None:
    manager = SessionStateManager()
    event = Event(session_id="session-1", type=ASR_PARTIAL)

    manager.append_event("session-1", event)

    assert manager.get_or_create("session-1").events == [event]


def test_reset_clears_session() -> None:
    manager = SessionStateManager()
    manager.get_or_create("session-1")

    manager.reset("session-1")

    assert manager.get("session-1") is None
