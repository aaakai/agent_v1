from __future__ import annotations

import asyncio
import struct

from audio_input import AudioFrame, AudioFeatureExtractor, BackchannelTrigger, EnergyVAD
from runtime import RuntimeCoordinator


def pcm16(*samples: int) -> bytes:
    return b"".join(struct.pack("<h", sample) for sample in samples)


def test_backchannel_trigger_consume_returns_decisions_and_updates_state() -> None:
    coordinator = RuntimeCoordinator()
    trigger = BackchannelTrigger(
        session_id="session-1",
        runtime_coordinator=coordinator,
        extractor=AudioFeatureExtractor(
            vad=EnergyVAD(energy_threshold=0.01, min_speech_frames=1)
        ),
    )
    frame = AudioFrame(
        session_id="session-1",
        timestamp_ms=1000,
        pcm=pcm16(10000, -10000),
    )

    decisions = asyncio.run(trigger.consume(frame))

    state = coordinator.get_session_state("session-1")
    assert isinstance(decisions, list)
    assert state.user_audio.is_speaking is True
    assert state.user_audio.energy > 0


def test_backchannel_trigger_speech_then_pause_can_play_backchannel() -> None:
    coordinator = RuntimeCoordinator()
    trigger = BackchannelTrigger(
        session_id="session-1",
        runtime_coordinator=coordinator,
        extractor=AudioFeatureExtractor(
            vad=EnergyVAD(energy_threshold=0.01, min_speech_frames=2)
        ),
    )

    async def run_frames() -> list[dict]:
        all_decisions: list[dict] = []
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
            all_decisions.extend(await trigger.consume(frame))
        return all_decisions

    decisions = asyncio.run(run_frames())

    state = coordinator.get_session_state("session-1")
    assert state.user_audio.backchannel_opportunity == 0.85
    assert any(
        decision.get("proposal_action") == "BACKCHANNEL"
        and decision.get("decision") == "play"
        and decision.get("lane") == "speech"
        for decision in decisions
    )


def test_backchannel_trigger_calls_on_features_and_merges_decisions() -> None:
    coordinator = RuntimeCoordinator()
    seen_features: list[dict] = []

    async def on_features(features: dict) -> list[dict]:
        seen_features.append(features)
        return [{"decision": "flush", "reason": "test"}]

    trigger = BackchannelTrigger(
        session_id="session-1",
        runtime_coordinator=coordinator,
        extractor=AudioFeatureExtractor(
            vad=EnergyVAD(energy_threshold=0.01, min_speech_frames=1)
        ),
        on_features=on_features,
    )

    decisions = asyncio.run(
        trigger.consume(
            AudioFrame(
                session_id="session-1",
                timestamp_ms=1000,
                pcm=pcm16(10000, -10000),
            )
        )
    )

    assert seen_features
    assert {"decision": "flush", "reason": "test"} in decisions
