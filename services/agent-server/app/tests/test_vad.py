from __future__ import annotations

import struct

from audio_input import AudioFrame, EnergyVAD


def pcm16(*samples: int) -> bytes:
    return b"".join(struct.pack("<h", sample) for sample in samples)


def test_empty_pcm_has_zero_rms() -> None:
    vad = EnergyVAD()

    assert vad.calculate_rms(b"") == 0.0


def test_silence_is_not_speech() -> None:
    vad = EnergyVAD()
    frame = AudioFrame(session_id="session-1", pcm=pcm16(0, 0, 0, 0))

    assert vad.is_speech(frame) is False


def test_nonzero_pcm_has_positive_rms() -> None:
    vad = EnergyVAD()

    assert vad.calculate_rms(pcm16(1000, -1000, 1000, -1000)) > 0


def test_odd_length_pcm_is_safely_truncated() -> None:
    vad = EnergyVAD()

    assert vad.calculate_rms(pcm16(1000) + b"\x00") > 0


def test_consecutive_speech_frames_enter_speech_state() -> None:
    vad = EnergyVAD(energy_threshold=0.01, min_speech_frames=2)
    frame = AudioFrame(session_id="session-1", pcm=pcm16(8000, -8000))

    first = vad.update(frame)
    second = vad.update(frame)

    assert first["state"] == "silence"
    assert second["is_speech"] is True
    assert second["speech_frames"] == 2
    assert second["state"] == "speech"


def test_consecutive_silence_frames_enter_silence_state() -> None:
    vad = EnergyVAD(
        energy_threshold=0.01,
        min_speech_frames=1,
        min_silence_frames=2,
    )
    speech = AudioFrame(session_id="session-1", pcm=pcm16(8000, -8000))
    silence = AudioFrame(session_id="session-1", pcm=pcm16(0, 0))
    vad.update(speech)

    first_silence = vad.update(silence)
    second_silence = vad.update(silence)

    assert first_silence["state"] == "speech"
    assert second_silence["silence_frames"] == 2
    assert second_silence["state"] == "silence"
