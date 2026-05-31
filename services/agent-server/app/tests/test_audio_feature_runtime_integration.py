from __future__ import annotations

import asyncio
import struct

from audio_input import (
    AudioFrame,
    AudioFeatureExtractor,
    BackchannelTrigger,
    EnergyVAD,
    RawAudioRouter,
)
from runtime import RuntimeCoordinator
from schemas import Event
from schemas.event_types import AUDIO_FEATURE_UPDATE


def pcm16(*samples: int) -> bytes:
    return b"".join(struct.pack("<h", sample) for sample in samples)


def test_runtime_coordinator_updates_audio_feature_fields() -> None:
    coordinator = RuntimeCoordinator()

    coordinator.process_event(
        Event(
            session_id="session-1",
            type=AUDIO_FEATURE_UPDATE,
            payload={
                "is_speaking": True,
                "energy": 0.25,
                "pause_ms": 240,
                "emotion": "thinking",
                "backchannel_opportunity": 0.85,
                "barge_in_score": 0.6,
            },
        )
    )

    state = coordinator.get_session_state("session-1")
    assert state.user_audio.is_speaking is True
    assert state.user_audio.energy == 0.25
    assert state.user_audio.pause_ms == 240
    assert state.user_audio.emotion == "thinking"
    assert state.user_audio.backchannel_opportunity == 0.85
    assert state.user_audio.barge_in_score == 0.6


def test_backchannel_trigger_can_run_as_raw_audio_router_consumer() -> None:
    coordinator = RuntimeCoordinator()
    trigger = BackchannelTrigger(
        session_id="session-1",
        runtime_coordinator=coordinator,
        extractor=AudioFeatureExtractor(
            vad=EnergyVAD(energy_threshold=0.01, min_speech_frames=2)
        ),
    )
    router = RawAudioRouter()
    router.add_consumer("backchannel_trigger", trigger.consume)

    async def route_frames() -> None:
        frames = [
            AudioFrame(
                session_id="session-1",
                timestamp_ms=1000,
                pcm=pcm16(10000, -10000),
            ),
            AudioFrame(
                session_id="session-1",
                timestamp_ms=1100,
                pcm=pcm16(10000, -10000),
            ),
            AudioFrame(
                session_id="session-1",
                timestamp_ms=1350,
                pcm=pcm16(0, 0),
            ),
        ]
        for frame in frames:
            await router.route(frame)

    asyncio.run(route_frames())

    state = coordinator.get_session_state("session-1")
    assert router.routed_count == 3
    assert state.user_audio.backchannel_opportunity == 0.85
    assert state.events[-1].type == AUDIO_FEATURE_UPDATE
