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
            "LiveKit real audio frame conversion is not implemented yet"
        )
        if False:
            yield AudioFrame(session_id=self.session_id)

    def _convert_livekit_frame_to_audio_frame(self, lk_frame: Any) -> AudioFrame:
        data = getattr(lk_frame, "data", None)
        if data is None:
            data = getattr(lk_frame, "pcm", None)
        if data is None:
            raise ValueError("LiveKit audio frame is missing PCM data")
        if isinstance(data, memoryview):
            pcm = data.tobytes()
        elif isinstance(data, bytearray):
            pcm = bytes(data)
        elif isinstance(data, bytes):
            pcm = data
        else:
            try:
                pcm = bytes(data)
            except TypeError as exc:
                raise ValueError("LiveKit audio frame data is not bytes-like") from exc

        sample_rate = int(getattr(lk_frame, "sample_rate", self.sample_rate))
        channels = int(
            getattr(
                lk_frame,
                "num_channels",
                getattr(lk_frame, "channels", self.channels),
            )
        )
        samples_per_channel = getattr(lk_frame, "samples_per_channel", None)
        if samples_per_channel is not None:
            samples_per_channel = int(samples_per_channel)

        return AudioFrame(
            session_id=self.session_id,
            sample_rate=sample_rate,
            channels=channels,
            samples_per_channel=samples_per_channel,
            pcm=pcm,
            source="livekit",
            metadata={
                "track_sid": getattr(self.track, "sid", None),
            },
        )
