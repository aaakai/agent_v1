from __future__ import annotations

import asyncio

import pytest

from audio_input import AudioFrame, RawAudioRouter
from livekit import LiveKitConfig, LiveKitDebugState, LiveKitRoomHandler, MockAudioTrackReader
from runtime import RuntimeCoordinator
from schemas.event_types import USER_AUDIO_FRAME


def test_room_handler_processes_mock_audio_reader() -> None:
    frames = [
        AudioFrame(session_id="session-1", frame_id="frame-1"),
        AudioFrame(session_id="session-1", frame_id="frame-2"),
    ]
    router = RawAudioRouter()
    seen: list[str] = []
    router.add_consumer("recorder", lambda frame: seen.append(frame.frame_id))
    coordinator = RuntimeCoordinator()
    handler = LiveKitRoomHandler(
        config=LiveKitConfig(),
        raw_audio_router=router,
        runtime_coordinator=coordinator,
    )

    result = asyncio.run(handler.handle_audio_reader(MockAudioTrackReader(frames)))

    assert result == {"frames_processed": 2, "errors": []}
    assert seen == ["frame-1", "frame-2"]
    assert router.routed_count == 2
    state = coordinator.get_session_state("session-1")
    assert len(state.events) == 2
    assert [event.type for event in state.events] == [USER_AUDIO_FRAME, USER_AUDIO_FRAME]


def test_room_handler_updates_livekit_debug_state() -> None:
    frames = [
        AudioFrame(session_id="session-1", frame_id="frame-1"),
        AudioFrame(session_id="session-1", frame_id="frame-2"),
    ]
    debug_state = LiveKitDebugState()
    seen: list[str] = []
    router = RawAudioRouter()
    router.add_consumer("seen", lambda frame: seen.append(frame.frame_id))
    handler = LiveKitRoomHandler(
        config=LiveKitConfig(),
        raw_audio_router=router,
        debug_state=debug_state,
    )

    result = asyncio.run(handler.handle_audio_reader(MockAudioTrackReader(frames)))

    assert result["frames_processed"] == 2
    assert seen == ["frame-1", "frame-2"]
    assert debug_state.frames_received == 2
    assert debug_state.events[-1].type == "frame_received"


def test_room_handler_collects_route_errors() -> None:
    frame = AudioFrame(session_id="session-1", frame_id="frame-1")
    router = RawAudioRouter()

    def failing_consumer(received: AudioFrame) -> None:
        raise RuntimeError("bad frame")

    router.add_consumer("bad", failing_consumer)
    handler = LiveKitRoomHandler(config=LiveKitConfig(), raw_audio_router=router)

    result = asyncio.run(handler.handle_audio_reader(MockAudioTrackReader([frame])))

    assert result["frames_processed"] == 1
    assert result["errors"] == [{"consumer": "bad", "error": "bad frame"}]


def test_room_handler_start_reader_task_processes_frames() -> None:
    async def run() -> None:
        frame = AudioFrame(session_id="session-1", frame_id="frame-1")
        handler = LiveKitRoomHandler(config=LiveKitConfig())
        task = handler.start_reader_task(MockAudioTrackReader([frame]), track_id="track-1")
        result = await task

        assert result["frames_processed"] == 1
        assert handler.frames_processed_total == 1
        assert "track-1" not in handler.active_reader_tasks

    asyncio.run(run())


def test_room_handler_reader_error_is_recorded() -> None:
    class BrokenReader(MockAudioTrackReader):
        async def read_frames(self):
            raise RuntimeError("reader failed")
            if False:
                yield AudioFrame(session_id="session-1")

    debug_state = LiveKitDebugState()
    handler = LiveKitRoomHandler(config=LiveKitConfig(), debug_state=debug_state)

    result = asyncio.run(handler.handle_audio_reader(BrokenReader([])))

    assert result["frames_processed"] == 0
    assert result["errors"] == [{"error": "reader failed"}]
    assert debug_state.events[-1].type == "reader_error"


def test_room_handler_stop_all_reader_tasks() -> None:
    async def run() -> None:
        class SlowReader(MockAudioTrackReader):
            async def read_frames(self):
                await asyncio.sleep(10)
                if False:
                    yield AudioFrame(session_id="session-1")

        handler = LiveKitRoomHandler(config=LiveKitConfig())
        handler.start_reader_task(SlowReader([]), track_id="slow")
        assert handler.active_reader_tasks
        await handler.stop_all_reader_tasks()
        assert handler.active_reader_tasks == {}

    asyncio.run(run())


def test_room_handler_start_rejects_incomplete_config() -> None:
    handler = LiveKitRoomHandler(config=LiveKitConfig())

    with pytest.raises(ValueError, match="LiveKit config is incomplete"):
        asyncio.run(handler.start())
