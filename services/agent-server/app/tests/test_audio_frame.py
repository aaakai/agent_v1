from __future__ import annotations

from audio_input import AudioFrame


def test_audio_frame_generates_id_and_timestamp() -> None:
    frame = AudioFrame(session_id="session-1")

    assert frame.frame_id
    assert frame.timestamp_ms > 0
    assert frame.sample_rate == 16000
    assert frame.channels == 1
    assert frame.pcm == b""
    assert frame.metadata == {}


def test_audio_frame_duration_ms_uses_samples_per_channel() -> None:
    frame = AudioFrame(
        session_id="session-1",
        sample_rate=16000,
        samples_per_channel=160,
    )

    assert frame.duration_ms == 10.0


def test_audio_frame_duration_is_none_without_sample_count() -> None:
    frame = AudioFrame(session_id="session-1")

    assert frame.duration_ms is None


def test_audio_frame_is_empty_tracks_pcm_length() -> None:
    assert AudioFrame(session_id="session-1").is_empty is True
    assert AudioFrame(session_id="session-1", pcm=b"\x00\x01").is_empty is False
