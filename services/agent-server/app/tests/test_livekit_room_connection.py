from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import livekit.room_connection as room_connection
from livekit.room_connection import (
    connect_room,
    create_livekit_room,
    disconnect_room,
    import_livekit_rtc,
    register_room_event,
)


class MockRoom:
    def __init__(self) -> None:
        self.events: dict[str, object] = {}
        self.connected: tuple[str, str] | None = None
        self.disconnected = False

    def on(self, event_name: str, callback: object) -> None:
        self.events[event_name] = callback

    async def connect(self, url: str, token: str) -> None:
        self.connected = (url, token)

    async def disconnect(self) -> None:
        self.disconnected = True


def test_create_livekit_room_uses_mock_rtc() -> None:
    rtc = SimpleNamespace(Room=MockRoom)

    room = create_livekit_room(rtc)

    assert isinstance(room, MockRoom)


def test_register_room_event_calls_room_on() -> None:
    room = MockRoom()
    callback = object()

    register_room_event(room, "connected", callback)

    assert room.events["connected"] is callback


def test_connect_and_disconnect_room_call_methods() -> None:
    room = MockRoom()

    asyncio.run(connect_room(room, "wss://example", "token"))
    asyncio.run(disconnect_room(room))

    assert room.connected == ("wss://example", "token")
    assert room.disconnected is True


def test_import_livekit_rtc_missing_error_is_clear(monkeypatch) -> None:
    def fail_import() -> object:
        raise ImportError("no livekit")

    monkeypatch.setattr(room_connection, "_import_external_livekit_rtc", fail_import)

    with pytest.raises(RuntimeError, match="LiveKit Python SDK is not installed"):
        import_livekit_rtc()
