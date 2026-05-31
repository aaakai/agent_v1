from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from typing import Any

from audio_input import AudioFrame


def _load_livekit_rtc() -> Any:
    try:
        return importlib.import_module("livekit.rtc")
    except Exception as exc:  # noqa: BLE001 - SDK absence should be normalized.
        raise RuntimeError("LiveKit SDK is not installed") from exc


class BaseAudioTrackPublisher(ABC):
    @abstractmethod
    async def publish_frame(self, frame: AudioFrame) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError


class MockAudioTrackPublisher(BaseAudioTrackPublisher):
    def __init__(self) -> None:
        self.published_frames: list[AudioFrame] = []
        self.stopped = False

    async def publish_frame(self, frame: AudioFrame) -> None:
        self.published_frames.append(frame)

    async def stop(self) -> None:
        self.stopped = True


class LiveKitAudioTrackPublisher(BaseAudioTrackPublisher):
    def __init__(self, room: Any, track_name: str = "assistant-audio") -> None:
        self.room = room
        self.track_name = track_name

    async def publish_frame(self, frame: AudioFrame) -> None:
        _load_livekit_rtc()
        raise NotImplementedError(
            "LiveKit audio publishing is not implemented yet"
        )

    async def stop(self) -> None:
        _load_livekit_rtc()
        raise NotImplementedError(
            "LiveKit audio publisher stop is not implemented yet"
        )
