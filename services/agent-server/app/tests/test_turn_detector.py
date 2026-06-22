from __future__ import annotations

import json

from audio_input.turn_detector import TurnDetector


def test_turn_detector_speaking_does_not_flush() -> None:
    detector = TurnDetector(silence_flush_ms=700)

    result = detector.update_from_features({"timestamp_ms": 1000, "is_speaking": True})

    assert result.should_flush_asr is False
    assert detector.snapshot()["turn_open"] is True


def test_turn_detector_silence_threshold_flushes_once() -> None:
    detector = TurnDetector(silence_flush_ms=700)
    detector.update_from_features({"timestamp_ms": 1000, "is_speaking": True})

    early = detector.update_from_features(
        {"timestamp_ms": 1500, "is_speaking": False, "pause_ms": 500}
    )
    flush = detector.update_from_features(
        {"timestamp_ms": 1800, "is_speaking": False, "pause_ms": 800}
    )
    duplicate = detector.update_from_features(
        {"timestamp_ms": 1900, "is_speaking": False, "pause_ms": 900}
    )

    assert early.should_flush_asr is False
    assert flush.should_flush_asr is True
    assert flush.reason == "silence"
    assert duplicate.should_flush_asr is False


def test_turn_detector_new_speech_allows_second_flush() -> None:
    detector = TurnDetector(silence_flush_ms=100)
    detector.update_from_features({"timestamp_ms": 1000, "is_speaking": True})
    assert detector.update_from_features(
        {"timestamp_ms": 1200, "is_speaking": False, "pause_ms": 100}
    ).should_flush_asr

    detector.update_from_features({"timestamp_ms": 1300, "is_speaking": True})
    second = detector.update_from_features(
        {"timestamp_ms": 1500, "is_speaking": False, "pause_ms": 100}
    )

    assert second.should_flush_asr is True


def test_turn_detector_user_speech_end_and_timeout() -> None:
    detector = TurnDetector(max_turn_ms=500)
    detector.update_from_features({"timestamp_ms": 1000, "is_speaking": True})

    assert detector.update_from_timeout(1600).reason == "max_turn_duration"

    detector.reset()
    detector.update_from_features({"timestamp_ms": 2000, "is_speaking": True})
    end = detector.update_from_user_speech_end(2100)

    assert end.should_flush_asr is True
    assert end.reason == "user_speech_end"
    json.dumps(detector.snapshot())
