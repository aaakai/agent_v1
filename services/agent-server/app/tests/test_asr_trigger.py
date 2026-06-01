from __future__ import annotations

import asyncio

from asr import ASRResult, ASRTrigger, MockASRAdapter
from audio_input import AudioFrame
from runtime import RuntimeCoordinator
from schemas.event_types import ASR_FINAL, ASR_PARTIAL


def test_result_to_event_maps_partial_and_final() -> None:
    coordinator = RuntimeCoordinator()
    trigger = ASRTrigger(
        session_id="session-1",
        runtime_coordinator=coordinator,
        asr_adapter=MockASRAdapter(),
    )

    partial = trigger.result_to_event(
        ASRResult(
            session_id="session-1",
            text="hello",
            is_final=False,
            stability=0.5,
            timestamp_ms=100,
            metadata={"lang": "zh"},
        )
    )
    final = trigger.result_to_event(
        ASRResult(session_id="session-1", text="done", is_final=True)
    )

    assert partial.type == ASR_PARTIAL
    assert partial.timestamp_ms == 100
    assert partial.payload == {
        "text": "hello",
        "stability": 0.5,
        "metadata": {"lang": "zh"},
    }
    assert final.type == ASR_FINAL
    assert final.payload["stability"] == 1.0


def test_consume_partial_updates_runtime_state() -> None:
    coordinator = RuntimeCoordinator()
    adapter = MockASRAdapter()
    trigger = ASRTrigger("session-1", coordinator, adapter)
    frame = AudioFrame(
        session_id="session-1",
        metadata={"asr_text": "partial"},
    )

    decisions = asyncio.run(trigger.consume(frame))

    state = coordinator.get_session_state("session-1")
    assert decisions == []
    assert state.asr.partial == "partial"
    assert trigger.started is True
    assert trigger.results_emitted == 1
    assert adapter.started_sessions == {"session-1"}


def test_consume_final_updates_runtime_state() -> None:
    coordinator = RuntimeCoordinator()
    trigger = ASRTrigger(
        "session-1",
        coordinator,
        MockASRAdapter(scripted_results=[
            {"session_id": "session-1", "text": "final", "is_final": True}
        ]),
    )

    asyncio.run(trigger.consume(AudioFrame(session_id="session-1")))

    state = coordinator.get_session_state("session-1")
    assert state.asr.final == "final"
    assert state.asr.partial is None


def test_close_calls_adapter_close() -> None:
    adapter = MockASRAdapter()
    trigger = ASRTrigger("session-1", RuntimeCoordinator(), adapter)

    asyncio.run(trigger.close())

    assert adapter.closed is True
