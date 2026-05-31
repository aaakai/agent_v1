from __future__ import annotations

import asyncio

import pytest

from audio_input import AudioFrame
from livekit import LiveKitAudioTrackReader, MockAudioTrackReader


def test_mock_audio_track_reader_yields_frames() -> None:
    frames = [
        AudioFrame(session_id="session-1", frame_id="frame-1"),
        AudioFrame(session_id="session-1", frame_id="frame-2"),
    ]
    reader = MockAudioTrackReader(frames)

    async def collect() -> list[AudioFrame]:
        return [frame async for frame in reader.read_frames()]

    assert asyncio.run(collect()) == frames


def test_livekit_audio_track_reader_imports_without_sdk() -> None:
    assert LiveKitAudioTrackReader is not None


def test_livekit_audio_track_reader_rejects_none_track() -> None:
    with pytest.raises(ValueError, match="track must not be None"):
        LiveKitAudioTrackReader(track=None, session_id="session-1")
