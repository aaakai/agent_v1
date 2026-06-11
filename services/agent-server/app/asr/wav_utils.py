from __future__ import annotations

import io
import wave

from audio_input import AudioFrame


def pcm_frames_to_wav_bytes(
    frames: list[AudioFrame],
    sample_rate: int | None = None,
    channels: int | None = None,
    sample_width: int = 2,
) -> bytes:
    if not frames:
        raise ValueError("frames must not be empty")

    resolved_sample_rate = sample_rate or frames[0].sample_rate
    resolved_channels = channels or frames[0].channels
    pcm = b"".join(frame.pcm for frame in frames if frame.pcm)
    if not pcm:
        raise ValueError("frames do not contain PCM data")

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(resolved_channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(resolved_sample_rate)
        wav.writeframes(pcm)
    return buffer.getvalue()


def estimate_audio_duration_ms(
    frames: list[AudioFrame],
    sample_width: int = 2,
) -> int:
    total_ms = 0.0
    for frame in frames:
        if frame.duration_ms is not None:
            total_ms += frame.duration_ms
            continue
        if frame.samples_per_channel is not None:
            total_ms += frame.samples_per_channel / frame.sample_rate * 1000
            continue
        if frame.pcm:
            samples = len(frame.pcm) / (sample_width * frame.channels)
            total_ms += samples / frame.sample_rate * 1000
    return int(total_ms)


def normalize_frames_for_asr(
    frames: list[AudioFrame],
    target_sample_rate: int | None = None,
) -> list[AudioFrame]:
    if target_sample_rate is None:
        return frames
    for frame in frames:
        if frame.sample_rate != target_sample_rate:
            raise NotImplementedError("Audio resampling is not implemented yet")
    return frames
