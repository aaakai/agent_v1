from __future__ import annotations

import asyncio

from asr import ASRTrigger, DeepgramASRAdapter, FunASRASRAdapter, MockASRAdapter
from asr import OpenAIRealtimeASRAdapter
from audio_input import AudioFrame, RawAudioRouter
from runtime import RuntimeCoordinator
from schemas import Event
from schemas.event_types import AUDIO_FEATURE_UPDATE, USER_SPEECH_END


def test_audio_barge_in_outputs_stop_speaking() -> None:
    coordinator = RuntimeCoordinator()
    state = coordinator.get_session_state("session-1")
    state.assistant.is_speaking = True

    decisions = coordinator.process_event(
        Event(
            session_id="session-1",
            type=AUDIO_FEATURE_UPDATE,
            payload={
                "is_speaking": True,
                "barge_in_score": 0.9,
            },
        )
    )

    assert any(
        decision.get("control_action") == "STOP_SPEAKING"
        and decision.get("control_reason") == "user_barge_in"
        for decision in decisions
    )


def test_asr_dangerous_partial_sets_followup_metadata() -> None:
    coordinator = RuntimeCoordinator()
    trigger = ASRTrigger(
        "session-1",
        coordinator,
        MockASRAdapter(),
    )
    frame = AudioFrame(
        session_id="session-1",
        metadata={"asr_text": "我准备直接删库"},
    )

    decisions = asyncio.run(trigger.consume(frame))

    state = coordinator.get_session_state("session-1")
    assert any(
        decision.get("control_action") == "INTERRUPT_USER"
        and decision.get("control_reason") == "dangerous_operation"
        for decision in decisions
    )
    assert state.metadata["interrupt_reason"] == "dangerous_operation"
    assert state.metadata["interrupt_phrase"] == "等一下，先别操作。"
    assert state.metadata["followup_needed"] is True
    assert state.metadata["followup_emitted"] is False


def test_asr_factual_error_partial_outputs_interrupt_user() -> None:
    coordinator = RuntimeCoordinator()
    trigger = ASRTrigger("session-1", coordinator, MockASRAdapter())
    frame = AudioFrame(
        session_id="session-1",
        metadata={"asr_text": "一加一等于三"},
    )

    decisions = asyncio.run(trigger.consume(frame))

    assert any(
        decision.get("control_action") == "INTERRUPT_USER"
        and decision.get("control_reason") == "obvious_factual_error"
        for decision in decisions
    )


def test_stop_speaking_has_priority_over_dangerous_semantic_interrupt() -> None:
    coordinator = RuntimeCoordinator()
    state = coordinator.get_session_state("session-1")
    state.assistant.is_speaking = True
    state.user_audio.is_speaking = True
    state.user_audio.barge_in_score = 0.9
    trigger = ASRTrigger("session-1", coordinator, MockASRAdapter())

    decisions = asyncio.run(
        trigger.consume(
            AudioFrame(
                session_id="session-1",
                metadata={"asr_text": "我要删库"},
            )
        )
    )

    assert any(
        decision.get("control_action") == "STOP_SPEAKING"
        for decision in decisions
    )
    assert not any(
        decision.get("control_action") == "INTERRUPT_USER"
        for decision in decisions
    )


def test_dialogue_followup_emits_after_user_stops_and_does_not_repeat() -> None:
    coordinator = RuntimeCoordinator()
    trigger = ASRTrigger("session-1", coordinator, MockASRAdapter())
    asyncio.run(
        trigger.consume(
            AudioFrame(
                session_id="session-1",
                metadata={"asr_text": "我准备直接删库"},
            )
        )
    )
    coordinator.process_event(
        Event(
            session_id="session-1",
            type=AUDIO_FEATURE_UPDATE,
            payload={"is_speaking": True},
        )
    )
    speaking_state = coordinator.get_session_state("session-1")
    assert speaking_state.metadata["followup_emitted"] is False

    first_followup = coordinator.process_event(
        Event(session_id="session-1", type=USER_SPEECH_END)
    )
    second_followup = coordinator.process_event(
        Event(session_id="session-1", type=USER_SPEECH_END)
    )

    assert any(
        decision.get("proposal_action") == "SPEAK"
        and decision.get("agent") == "dialogue"
        for decision in first_followup
    )
    assert coordinator.get_session_state("session-1").metadata["followup_emitted"] is True
    assert not any(
        decision.get("proposal_action") == "SPEAK"
        and decision.get("agent") == "dialogue"
        for decision in second_followup
    )


def test_asr_trigger_can_run_as_raw_audio_router_consumer() -> None:
    coordinator = RuntimeCoordinator()
    trigger = ASRTrigger("session-1", coordinator, MockASRAdapter())
    router = RawAudioRouter()
    router.add_consumer("asr", trigger.consume)

    asyncio.run(
        router.route(
            AudioFrame(
                session_id="session-1",
                metadata={"asr_text": "router partial"},
            )
        )
    )

    assert trigger.results_emitted == 1
    assert coordinator.get_session_state("session-1").asr.partial == "router partial"


def test_provider_placeholders_are_importable() -> None:
    assert OpenAIRealtimeASRAdapter is not None
    assert DeepgramASRAdapter is not None
    assert FunASRASRAdapter is not None
