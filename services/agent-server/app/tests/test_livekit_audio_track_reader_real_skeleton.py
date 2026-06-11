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


class MockBytesLike:
    def tobytes(self) -> bytes:
        return b"\x03\x00\x04\x00"


class MockEvent:
    frame = MockLiveKitFrame()


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


def test_convert_accepts_bytearray_and_tobytes_payloads() -> None:
    reader = LiveKitAudioTrackReader(track=MockTrack(), session_id="session-1")

    bytearray_frame = type("BytearrayFrame", (), {"data": bytearray(b"\x01\x00")})()
    tobytes_frame = type("BytesLikeFrame", (), {"data": MockBytesLike()})()

    assert reader._convert_livekit_frame_to_audio_frame(bytearray_frame).pcm == b"\x01\x00"
    assert reader._convert_livekit_frame_to_audio_frame(tobytes_frame).pcm == b"\x03\x00\x04\x00"


def test_extract_event_frame_payload() -> None:
    reader = LiveKitAudioTrackReader(track=MockTrack(), session_id="session-1")

    payload = reader._extract_audio_frame_payload(MockEvent())

    assert isinstance(payload, MockLiveKitFrame)


def test_reader_sdk_missing_error_is_clear(monkeypatch) -> None:
    import livekit.audio_track_reader as reader_module

    def fail_load() -> object:
        raise RuntimeError("LiveKit SDK is not installed")

    monkeypatch.setattr(reader_module, "_load_livekit_rtc", fail_load)
    reader = LiveKitAudioTrackReader(track=MockTrack(), session_id="session-1")

    with pytest.raises(RuntimeError, match="LiveKit SDK is not installed"):
        async def consume() -> None:
            async for _frame in reader.read_frames():
                pass

        import asyncio

        asyncio.run(consume())


def test_reader_none_track_error_is_clear() -> None:
    with pytest.raises(ValueError, match="track must not be None"):
        LiveKitAudioTrackReader(track=None, session_id="session-1")
