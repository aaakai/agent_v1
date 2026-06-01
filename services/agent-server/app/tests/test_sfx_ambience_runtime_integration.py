from __future__ import annotations

from audio_runtime import AmbienceController
from orchestrator import AudioOrchestrator
from runtime import RuntimeCoordinator
from schemas import Event, SessionState
from schemas.event_types import ASR_FINAL, ASSISTANT_SPEECH_START, SCENE_CHANGED


def test_asr_final_door_knock_generates_spatial_sfx_decision() -> None:
    coordinator = RuntimeCoordinator()

    decisions = coordinator.process_event(
        Event(
            session_id="session-1",
            type=ASR_FINAL,
            payload={"text": "突然有人敲门"},
        )
    )

    assert any(
        decision.get("proposal_action") == "PLAY_SFX"
        and decision.get("lane") == "sfx"
        for decision in decisions
    )
    state = coordinator.get_session_state("session-1")
    sfx = state.audio_runtime.sfx_playing[0]
    assert sfx["metadata"]["event"] == "door_knock"
    assert sfx["metadata"]["spatial"]["azimuth_deg"] == -30.0
    assert sfx["metadata"]["spatial"]["reverb"] == "small_room"


def test_scene_changed_updates_runtime_scene() -> None:
    coordinator = RuntimeCoordinator()

    coordinator.process_event(
        Event(
            session_id="session-1",
            type=SCENE_CHANGED,
            payload={
                "name": "rainy_alley",
                "mood": "tense",
                "ambience": "rain_alley_loop",
                "metadata": {"reverb": "wet_alley"},
            },
        )
    )

    state = coordinator.get_session_state("session-1")
    assert state.scene.name == "rainy_alley"
    assert state.scene.mood == "tense"
    assert state.scene.ambience == "rain_alley_loop"
    assert state.scene.metadata["reverb"] == "wet_alley"


def test_ambience_controller_proposal_is_handled_by_orchestrator() -> None:
    orchestrator = AudioOrchestrator()
    state = SessionState(session_id="session-1")
    proposal = AmbienceController().ambience_for_scene("session-1", "rainy_alley")

    decision = orchestrator.handle_output_proposal(proposal, state=state, now_ms=1000)

    assert decision["decision"] == "play"
    assert decision["lane"] == "ambience"
    assert decision["duck"] is False
    assert state.audio_runtime.ambience_playing == proposal.proposal_id


def test_sfx_and_ambience_duck_while_speech_busy() -> None:
    coordinator = RuntimeCoordinator()
    coordinator.process_event(Event(session_id="session-1", type=ASSISTANT_SPEECH_START))
    sfx_decisions = coordinator.process_event(
        Event(
            session_id="session-1",
            type=ASR_FINAL,
            payload={"text": "突然有人敲门"},
        )
    )
    state = coordinator.get_session_state("session-1")
    ambience = AmbienceController().ambience_for_scene("session-1", "rainy_alley")
    ambience_decision = coordinator.orchestrator.handle_output_proposal(
        ambience,
        state=state,
        now_ms=1000,
    )

    assert any(
        decision.get("lane") == "sfx" and decision.get("duck") is True
        for decision in sfx_decisions
    )
    assert ambience_decision["lane"] == "ambience"
    assert ambience_decision["duck"] is True
