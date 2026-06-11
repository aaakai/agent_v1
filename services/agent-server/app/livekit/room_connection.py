from __future__ import annotations

import inspect
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


def import_livekit_rtc() -> Any:
    try:
        return _import_external_livekit_rtc()
    except Exception as exc:  # noqa: BLE001 - normalize optional SDK failures.
        raise RuntimeError(
            "LiveKit Python SDK is not installed. Install livekit to enable real room connection."
        ) from exc


def create_livekit_room(rtc_module: Any | None = None) -> Any:
    rtc = rtc_module or import_livekit_rtc()
    room_class = getattr(rtc, "Room", None)
    if room_class is None:
        raise RuntimeError("LiveKit rtc.Room is not available")
    return room_class()


def register_room_event(room: Any, event_name: str, callback: Callable[..., Any]) -> None:
    on = getattr(room, "on", None)
    if not callable(on):
        raise RuntimeError("LiveKit room does not support event registration")
    on(event_name, callback)


async def connect_room(room: Any, url: str, token: str) -> None:
    connect = getattr(room, "connect", None)
    if not callable(connect):
        raise RuntimeError("LiveKit room does not support connect")
    result = connect(url, token)
    if inspect.isawaitable(result):
        await result


async def disconnect_room(room: Any) -> None:
    disconnect = getattr(room, "disconnect", None)
    if not callable(disconnect):
        return
    result = disconnect()
    if inspect.isawaitable(result):
        await result


def _import_external_livekit_rtc() -> Any:
    app_dir = str(Path(__file__).resolve().parents[1])
    saved_path = list(sys.path)
    saved_livekit = sys.modules.pop("livekit", None)
    saved_livekit_rtc = sys.modules.pop("livekit.rtc", None)
    try:
        sys.path = [
            path
            for path in sys.path
            if str(Path(path or ".").resolve()) != app_dir
        ]
        from livekit import rtc  # type: ignore[import-not-found]

        return rtc
    finally:
        sys.path = saved_path
        if saved_livekit is not None:
            sys.modules["livekit"] = saved_livekit
        if saved_livekit_rtc is not None:
            sys.modules["livekit.rtc"] = saved_livekit_rtc
