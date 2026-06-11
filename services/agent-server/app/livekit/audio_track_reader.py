from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from audio_input import AudioFrame

from .room_connection import import_livekit_rtc


def _load_livekit_rtc() -> Any:
    try:
        return import_livekit_rtc()
    except RuntimeError as exc:
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
        rtc = _load_livekit_rtc()
        audio_stream = self._create_audio_stream(rtc)
        async for event_or_frame in audio_stream:
            lk_frame = self._extract_audio_frame_payload(event_or_frame)
            yield self._convert_livekit_frame_to_audio_frame(lk_frame)

    def _create_audio_stream(self, rtc: Any) -> Any:
        audio_stream_cls = getattr(rtc, "AudioStream", None)
        if audio_stream_cls is None:
            raise RuntimeError("LiveKit AudioStream is not available")

        from_track = getattr(audio_stream_cls, "from_track", None)
        attempts: list[tuple[Any, tuple[Any, ...], dict[str, Any]]] = []
        if callable(from_track):
            attempts.append(
                (
                    from_track,
                    (),
                    {
                        "track": self.track,
                        "sample_rate": self.sample_rate,
                        "num_channels": self.channels,
                    },
                )
            )
        attempts.extend(
            [
                (
                    audio_stream_cls,
                    (self.track,),
                    {
                        "sample_rate": self.sample_rate,
                        "num_channels": self.channels,
                    },
                ),
                (audio_stream_cls, (self.track,), {}),
            ]
        )

        last_error: Exception | None = None
        for factory, args, kwargs in attempts:
            try:
                return factory(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - try SDK variants.
                last_error = exc
        raise RuntimeError("LiveKit AudioStream could not be created") from last_error

    def _extract_audio_frame_payload(self, lk_event_or_frame: Any) -> Any:
        frame = getattr(lk_event_or_frame, "frame", None)
        if frame is not None:
            return frame
        audio_frame = getattr(lk_event_or_frame, "audio_frame", None)
        if audio_frame is not None:
            return audio_frame
        return lk_event_or_frame

    def _convert_livekit_frame_to_audio_frame(self, lk_frame: Any) -> AudioFrame:
        data = getattr(lk_frame, "data", None)
        if data is None:
            data = getattr(lk_frame, "pcm", None)
        if data is None:
            raise ValueError(
                "LiveKit audio frame does not contain PCM data (missing PCM data)"
            )
        if hasattr(data, "tobytes"):
            pcm = data.tobytes()
        elif isinstance(data, memoryview):
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

        timestamp_ms = self._timestamp_ms(lk_frame)
        frame_kwargs: dict[str, Any] = {}
        if timestamp_ms is not None:
            frame_kwargs["timestamp_ms"] = timestamp_ms

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
            **frame_kwargs,
        )

    def _timestamp_ms(self, lk_frame: Any) -> int | None:
        timestamp_ms = getattr(lk_frame, "timestamp_ms", None)
        if timestamp_ms is not None:
            return int(timestamp_ms)
        timestamp_us = getattr(lk_frame, "timestamp_us", None)
        if timestamp_us is not None:
            return int(int(timestamp_us) / 1000)
        timestamp = getattr(lk_frame, "timestamp", None)
        if timestamp is None:
            return None
        timestamp_number = float(timestamp)
        if timestamp_number > 10_000_000_000:
            return int(timestamp_number / 1000)
        return int(timestamp_number)
