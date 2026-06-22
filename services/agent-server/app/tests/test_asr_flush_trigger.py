from __future__ import annotations

import asyncio
import json

from asr import ASRResult, ASRTrigger, BaseASRAdapter
from audio_input import AudioFrame
from audio_input.asr_flush_trigger import ASRFlushTrigger
from audio_input.turn_detector import TurnDetector
from runtime import RuntimeCoordinator
from schemas import Event
from schemas.event_types import AUDIO_FEATURE_UPDATE, USER_SPEECH_END


class FlushAdapter(BaseASRAdapter):
    def __init__(self, text: str = "final") -> None:
        self.text = text
        self.flush_calls = 0

    async def flush(self) -> list[ASRResult]:
        self.flush_calls += 1
        return [ASRResult(session_id="s1", text=self.text, is_final=True)]


class BrokenFlushAdapter(BaseASRAdapter):
    async def flush(self) -> list[ASRResult]:
        raise RuntimeError("flush failed")


def make_trigger(adapter: BaseASRAdapter | None = None) -> tuple[ASRFlushTrigger, RuntimeCoordinator, FlushAdapter | None]:
    coordinator = RuntimeCoordinator()
    concrete = adapter or FlushAdapter()
    asr_trigger = ASRTrigger("s1", coordinator, concrete)
    return (
        ASRFlushTrigger(
            "s1",
            asr_trigger,
            turn_detector=TurnDetector(silence_flush_ms=700),
            runtime_coordinator=coordinator,
        ),
        coordinator,
        concrete if isinstance(concrete, FlushAdapter) else None,
    )


def test_consume_features_silence_triggers_flush() -> None:
    trigger, coordinator, adapter = make_trigger()

    async def run():
        assert await trigger.consume_features({"timestamp_ms": 1000, "is_speaking": True}) == []
        return await trigger.consume_features(
            {"timestamp_ms": 1800, "is_speaking": False, "pause_ms": 800}
        )

    decisions = asyncio.run(run())

    assert adapter is not None and adapter.flush_calls == 1
    assert trigger.last_flush_reason == "silence"
    assert trigger.last_flush_at_ms is not None
    assert coordinator.get_session_state("s1").asr.final == "final"
    assert decisions
    status = trigger.get_status()
    assert status["last_flush_reason"] == "silence"
    assert status["last_flush_at_ms"] is not None
    assert status["timeline"][-1]["type"] == "flush"


def test_consume_event_user_speech_end_triggers_flush() -> None:
    trigger, coordinator, _adapter = make_trigger()

    async def run():
        await trigger.consume_features({"timestamp_ms": 1000, "is_speaking": True})
        return await trigger.consume_event(Event(session_id="s1", type=USER_SPEECH_END))

    asyncio.run(run())

    assert trigger.last_flush_reason == "user_speech_end"
    assert coordinator.get_session_state("s1").asr.final == "final"


def test_consume_audio_feature_event_and_force_turn_end_frame() -> None:
    trigger, coordinator, _adapter = make_trigger(FlushAdapter("forced"))

    async def run():
        await trigger.consume_event(
            Event(
                session_id="s1",
                type=AUDIO_FEATURE_UPDATE,
                payload={"timestamp_ms": 1000, "is_speaking": True},
            )
        )
        return await trigger.consume_frame(
            AudioFrame(session_id="s1", metadata={"force_turn_end": True})
        )

    asyncio.run(run())

    assert trigger.last_flush_reason == "debug_force_turn_end"
    assert coordinator.get_session_state("s1").asr.final == "forced"


def test_flush_error_recorded_and_status_json_friendly() -> None:
    trigger, _coordinator, _adapter = make_trigger(BrokenFlushAdapter())

    result = asyncio.run(trigger.flush("manual"))

    assert result[0]["type"] == "asr_error"
    assert trigger.errors
    assert trigger.get_status()["last_flush_at_ms"] is not None
    json.dumps(trigger.get_status(), ensure_ascii=False)
