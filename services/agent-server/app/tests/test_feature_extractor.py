from __future__ import annotations

import struct

from audio_input import AudioFeatureExtractor, AudioFrame, EnergyVAD
from schemas.event_types import AUDIO_FEATURE_UPDATE


def pcm16(*samples: int) -> bytes:
    return b"".join(struct.pack("<h", sample) for sample in samples)


def test_speech_frame_extracts_speaking_features() -> None:
    extractor = AudioFeatureExtractor(
        vad=EnergyVAD(energy_threshold=0.01, min_speech_frames=1)
    )
    frame = AudioFrame(
        session_id="session-1",
        frame_id="frame-1",
        timestamp_ms=1000,
        pcm=pcm16(10000, -10000),
    )

    features = extractor.extract(frame)

    assert features["frame_id"] == "frame-1"
    assert features["timestamp_ms"] == 1000
    assert features["energy"] > 0
    assert features["is_speaking"] is True
    assert features["pause_ms"] == 0
    assert features["barge_in_score"] == 0.6


def test_silence_after_speech_increases_pause_ms() -> None:
    extractor = AudioFeatureExtractor(
        vad=EnergyVAD(energy_threshold=0.01, min_speech_frames=1)
    )
    extractor.extract(
        AudioFrame(
            session_id="session-1",
            timestamp_ms=1000,
            pcm=pcm16(10000, -10000),
        )
    )

    features = extractor.extract(
        AudioFrame(
            session_id="session-1",
            timestamp_ms=1250,
            pcm=pcm16(0, 0),
        )
    )

    assert features["pause_ms"] == 250
    assert features["backchannel_opportunity"] == 0.85
    assert features["emotion"] == "thinking"


def test_pause_outside_backchannel_window_has_no_opportunity() -> None:
    extractor = AudioFeatureExtractor(
        vad=EnergyVAD(energy_threshold=0.01, min_speech_frames=1)
    )
    extractor.extract(
        AudioFrame(
            session_id="session-1",
            timestamp_ms=1000,
            pcm=pcm16(10000, -10000),
        )
    )

    features = extractor.extract(
        AudioFrame(
            session_id="session-1",
            timestamp_ms=1700,
            pcm=pcm16(0, 0),
        )
    )

    assert features["pause_ms"] == 700
    assert features["backchannel_opportunity"] == 0.0
    assert features["emotion"] is None


def test_to_event_generates_audio_feature_update() -> None:
    extractor = AudioFeatureExtractor()
    features = {
        "frame_id": "frame-1",
        "timestamp_ms": 1234,
        "energy": 0.2,
        "is_speaking": True,
        "pause_ms": 0,
        "backchannel_opportunity": 0.0,
        "barge_in_score": 0.6,
        "emotion": None,
    }

    event = extractor.to_event("session-1", features)

    assert event.session_id == "session-1"
    assert event.type == AUDIO_FEATURE_UPDATE
    assert event.source == "audio_feature_extractor"
    assert event.timestamp_ms == 1234
    assert event.payload == features
