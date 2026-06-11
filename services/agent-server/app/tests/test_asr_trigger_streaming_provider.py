from __future__ import annotations

import asyncio
import json

from asr import ASRDiagnosticsStore, ASRTrigger, BaseASRAdapter, MockStreamingASRAdapter
from audio_input import AudioFrame
from runtime import RuntimeCoordinator


def test_asr_trigger_streaming_partial_and_final_update_state() -> None:
    coordinator = RuntimeCoordinator()
    adapter = MockStreamingASRAdapter(
        scripted_results=[
            {"session_id": "s1", "text": "partial", "is_final": False},
            {"session_id": "s1", "text": "final", "is_final": True},
        ]
    )
    trigger = ASRTrigger("s1", coordinator, adapter)

    asyncio.run(trigger.consume(AudioFrame(session_id="s1")))
    asyncio.run(trigger.consume(AudioFrame(session_id="s1")))

    state = coordinator.get_session_state("s1")
    assert state.asr.final == "final"
    assert trigger.get_status()["results_emitted"] == 2
    json.dumps(trigger.get_status(), ensure_ascii=False)


def test_asr_trigger_dangerous_text_still_triggers_interrupt() -> None:
    coordinator = RuntimeCoordinator()
    trigger = ASRTrigger("s1", coordinator, MockStreamingASRAdapter())
    frame = AudioFrame(session_id="s1", metadata={"asr_text": "我准备直接删库"})

    decisions = asyncio.run(trigger.consume(frame))

    state = coordinator.get_session_state("s1")
    assert state.metadata["interrupt_reason"] == "dangerous_operation"
    assert any(decision.get("decision") == "no_op" for decision in decisions)


class BrokenASRAdapter(BaseASRAdapter):
    async def start_stream(self, session_id: str) -> None:
        raise RuntimeError("provider down")


def test_asr_trigger_provider_error_recorded() -> None:
    diagnostics = ASRDiagnosticsStore()
    trigger = ASRTrigger(
        "s1",
        RuntimeCoordinator(),
        BrokenASRAdapter(),
        diagnostics=diagnostics,
    )

    result = asyncio.run(trigger.consume(AudioFrame(session_id="s1")))

    assert result[0]["type"] == "asr_error"
    assert diagnostics.snapshot()["errors"][0]["error"] == "provider down"
