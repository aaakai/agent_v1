from __future__ import annotations

import pytest

from asr.wav_utils import (
    estimate_audio_duration_ms,
    normalize_frames_for_asr,
    pcm_frames_to_wav_bytes,
)
from audio_input import AudioFrame


def test_pcm_frames_to_wav_bytes_returns_riff_wave() -> None:
    frame = AudioFrame(
        session_id="s1",
        sample_rate=16000,
        channels=1,
        samples_per_channel=160,
        pcm=b"\x00\x00" * 160,
    )

    wav = pcm_frames_to_wav_bytes([frame])

    assert wav.startswith(b"RIFF")
    assert b"WAVE" in wav[:16]


def test_pcm_frames_to_wav_bytes_rejects_empty_frames() -> None:
    with pytest.raises(ValueError, match="frames must not be empty"):
        pcm_frames_to_wav_bytes([])


def test_pcm_frames_to_wav_bytes_rejects_all_empty_pcm() -> None:
    with pytest.raises(ValueError, match="PCM"):
        pcm_frames_to_wav_bytes([AudioFrame(session_id="s1", pcm=b"")])


def test_estimate_audio_duration_ms_uses_duration_or_pcm_length() -> None:
    frame_with_samples = AudioFrame(
        session_id="s1",
        sample_rate=16000,
        channels=1,
        samples_per_channel=1600,
        pcm=b"\x00\x00" * 1600,
    )
    frame_with_pcm = AudioFrame(
        session_id="s1",
        sample_rate=16000,
        channels=1,
        pcm=b"\x00\x00" * 1600,
    )

    assert estimate_audio_duration_ms([frame_with_samples]) == 100
    assert estimate_audio_duration_ms([frame_with_pcm]) == 100


def test_normalize_frames_rejects_sample_rate_mismatch() -> None:
    frame = AudioFrame(session_id="s1", sample_rate=8000)

    with pytest.raises(NotImplementedError, match="resampling"):
        normalize_frames_for_asr([frame], target_sample_rate=16000)
