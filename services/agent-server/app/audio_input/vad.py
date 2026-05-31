from __future__ import annotations

import math
import struct
from typing import Any

from .audio_frame import AudioFrame


class EnergyVAD:
    def __init__(
        self,
        energy_threshold: float = 0.01,
        min_speech_frames: int = 2,
        min_silence_frames: int = 3,
    ) -> None:
        self.energy_threshold = energy_threshold
        self.min_speech_frames = min_speech_frames
        self.min_silence_frames = min_silence_frames
        self.speech_frames = 0
        self.silence_frames = 0
        self.state = "silence"

    def calculate_rms(self, pcm: bytes, sample_width: int = 2) -> float:
        if not pcm:
            return 0.0
        if sample_width <= 0:
            raise ValueError("sample_width must be positive")

        usable_length = len(pcm) - (len(pcm) % sample_width)
        if usable_length <= 0:
            return 0.0
        pcm = pcm[:usable_length]

        if sample_width == 2:
            samples = [
                sample[0]
                for sample in struct.iter_unpack("<h", pcm)
            ]
            max_amplitude = 32768.0
        elif sample_width == 1:
            samples = [
                value - 128
                for value in pcm
            ]
            max_amplitude = 128.0
        else:
            raise ValueError("only 8-bit and 16-bit PCM are supported")

        if not samples:
            return 0.0
        mean_square = sum(sample * sample for sample in samples) / len(samples)
        return min(1.0, math.sqrt(mean_square) / max_amplitude)

    def is_speech(self, frame: AudioFrame) -> bool:
        if frame.is_empty:
            return False
        return self.calculate_rms(frame.pcm) >= self.energy_threshold

    def update(self, frame: AudioFrame) -> dict[str, Any]:
        rms = self.calculate_rms(frame.pcm)
        is_speech = bool(frame.pcm) and rms >= self.energy_threshold

        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1
            self.speech_frames = 0

        if self.speech_frames >= self.min_speech_frames:
            self.state = "speech"
        elif self.silence_frames >= self.min_silence_frames:
            self.state = "silence"

        return {
            "is_speech": is_speech,
            "rms": rms,
            "speech_frames": self.speech_frames,
            "silence_frames": self.silence_frames,
            "state": self.state,
        }
