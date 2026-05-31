from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from audio_input import AudioFrame


def _load_livekit_rtc() -> Any:
    try:
        return importlib.import_module("livekit.rtc")
    except Exception as exc:  # noqa: BLE001 - SDK absence should be normalized.
        raise RuntimeError("LiveKit SDK is not installed") from exc


class BaseAudioTrackReader(ABC):
    @abstractmethod
    async def read_frames(self) -> AsyncIterator[AudioFrame]:
        if False:
            yield AudioFrame(session_id="_abstract")


class MockAudioTrackReader(BaseAudioTrackReader):
    def __init__(self, frames: list[AudioFrame]) -> None:
        self.frames = frames

    async def read_frames(self) -> AsyncIterator[AudioFrame]:
        for frame in self.frames:
            yield frame


class LiveKitAudioTrackReader(BaseAudioTrackReader):
    def __init__(
        self,
        track: Any,
        session_id: str,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        if track is None:
            raise ValueError("track must not be None")
        self.track = track
        self.session_id = session_id
        self.sample_rate = sample_rate
        self.channels = channels

    async def read_frames(self) -> AsyncIterator[AudioFrame]:
        _load_livekit_rtc()
        raise NotImplementedError(
            "LiveKit audio stream conversion is not implemented yet"
        )
        if False:
            yield AudioFrame(session_id=self.session_id)
