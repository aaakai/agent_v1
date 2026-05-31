from __future__ import annotations

import asyncio

from audio_input import AudioFrame
from livekit import LiveKitAudioTrackPublisher, MockAudioTrackPublisher


def test_mock_audio_track_publisher_records_frames_and_stop() -> None:
    publisher = MockAudioTrackPublisher()
    frame = AudioFrame(session_id="session-1")

    asyncio.run(publisher.publish_frame(frame))
    asyncio.run(publisher.stop())

    assert publisher.published_frames == [frame]
    assert publisher.stopped is True


def test_livekit_audio_track_publisher_imports_without_sdk() -> None:
    assert LiveKitAudioTrackPublisher is not None
