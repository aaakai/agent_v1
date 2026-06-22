from __future__ import annotations

import asyncio

from asr import ASRResult, ASRTrigger, BaseASRAdapter
from runtime import RuntimeCoordinator


class ReasonFlushAdapter(BaseASRAdapter):
    async def flush(self) -> list[ASRResult]:
        return [
            ASRResult(
                session_id="s1",
                text="turn final",
                is_final=True,
                metadata={"existing": True},
            )
        ]


class ErrorFlushAdapter(BaseASRAdapter):
    async def flush(self) -> list[ASRResult]:
        raise RuntimeError("flush failed")


def test_asr_trigger_flush_reason_updates_metadata_and_state() -> None:
    coordinator = RuntimeCoordinator()
    trigger = ASRTrigger("s1", coordinator, ReasonFlushAdapter())

    decisions = asyncio.run(trigger.flush(reason="silence"))

    state = coordinator.get_session_state("s1")
    event = state.events[-1]
    assert state.asr.final == "turn final"
    assert event.payload["metadata"]["existing"] is True
    assert event.payload["metadata"]["flush_reason"] == "silence"
    assert event.payload["metadata"]["turn_final"] is True
    assert isinstance(event.payload["metadata"]["flushed_at_ms"], int)
    assert trigger.get_status()["flush_count"] == 1
    assert trigger.get_status()["diagnostics"]["flush_count"] == 1
    assert trigger.get_status()["diagnostics"]["last_final_text"] == "turn final"
    assert decisions


def test_asr_trigger_flush_error_does_not_raise() -> None:
    trigger = ASRTrigger("s1", RuntimeCoordinator(), ErrorFlushAdapter())

    result = asyncio.run(trigger.flush(reason="manual"))

    assert result[0]["type"] == "asr_error"
    assert trigger.get_status()["diagnostics"]["errors"][0]["error"] == "flush failed"
