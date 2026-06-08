from __future__ import annotations

import pytest

from livekit import LiveKitAudioTrackReader


class MockLiveKitFrame:
    data = b"\x01\x00\x02\x00"
    sample_rate = 48000
    num_channels = 2
    samples_per_channel = 1


class MockTrack:
    sid = "track-1"


def test_convert_mock_livekit_frame_to_audio_frame() -> None:
    reader = LiveKitAudioTrackReader(track=MockTrack(), session_id="session-1")

    frame = reader._convert_livekit_frame_to_audio_frame(MockLiveKitFrame())

    assert frame.session_id == "session-1"
    assert frame.sample_rate == 48000
    assert frame.channels == 2
    assert frame.samples_per_channel == 1
    assert frame.pcm == b"\x01\x00\x02\x00"
    assert frame.source == "livekit"
    assert frame.metadata["track_sid"] == "track-1"


def test_convert_rejects_missing_pcm_data() -> None:
    reader = LiveKitAudioTrackReader(track=MockTrack(), session_id="session-1")

    with pytest.raises(ValueError, match="missing PCM data"):
        reader._convert_livekit_frame_to_audio_frame(object())


def test_reader_none_track_error_is_clear() -> None:
    with pytest.raises(ValueError, match="track must not be None"):
        LiveKitAudioTrackReader(track=None, session_id="session-1")
