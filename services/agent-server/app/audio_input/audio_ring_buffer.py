from __future__ import annotations

from collections import deque

from .audio_frame import AudioFrame


class AudioRingBuffer:
    def __init__(self, max_frames: int = 500) -> None:
        if max_frames <= 0:
            raise ValueError("max_frames must be positive")
        self.frames: deque[AudioFrame] = deque(maxlen=max_frames)

    def append(self, frame: AudioFrame) -> None:
        self.frames.append(frame)

    def get_recent(self, count: int | None = None) -> list[AudioFrame]:
        frames = list(self.frames)
        if count is None:
            return frames
        if count <= 0:
            return []
        return frames[-count:]

    def clear(self) -> None:
        self.frames.clear()

    def __len__(self) -> int:
        return len(self.frames)

    def latest(self) -> AudioFrame | None:
        if not self.frames:
            return None
        return self.frames[-1]

    def get_since(self, timestamp_ms: int) -> list[AudioFrame]:
        return [
            frame
            for frame in self.frames
            if frame.timestamp_ms >= timestamp_ms
        ]
