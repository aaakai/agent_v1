from __future__ import annotations

import pytest

from audio_runtime import AmbienceController
from schemas import OutputProposal


def test_ambience_for_office_meeting() -> None:
    proposal = AmbienceController().ambience_for_scene("session-1", "office_meeting")

    assert proposal.lane == "ambience"
    assert proposal.action == "SET_AMBIENCE"
    assert proposal.metadata["asset"] == "office_room_tone"
    assert proposal.metadata["reverb"] == "small_room"
    assert proposal.mixing["gain"] == 0.18


def test_ambience_for_rainy_alley_and_spaceship() -> None:
    controller = AmbienceController()

    rainy = controller.ambience_for_scene("session-1", "rainy_alley")
    spaceship = controller.ambience_for_scene("session-1", "spaceship_cabin")

    assert rainy.metadata["asset"] == "rain_alley_loop"
    assert rainy.mixing["gain"] == 0.25
    assert spaceship.metadata["asset"] == "spaceship_hum_loop"
    assert spaceship.mixing["gain"] == 0.22


def test_unknown_scene_falls_back_to_default() -> None:
    proposal = AmbienceController().ambience_for_scene("session-1", "unknown")

    assert proposal.metadata["scene"] == "office_meeting"
    assert proposal.metadata["asset"] == "office_room_tone"


def test_ambience_state_from_proposal() -> None:
    controller = AmbienceController()
    proposal = controller.ambience_for_scene("session-1", "rainy_alley")

    state = controller.state_from_proposal(proposal)

    assert state.scene == "rainy_alley"
    assert state.asset == "rain_alley_loop"
    assert state.gain == 0.25
    assert state.loop is True
    assert state.fade_ms == 1200
    assert state.reverb == "wet_alley"


def test_state_from_non_ambience_proposal_raises() -> None:
    proposal = OutputProposal(
        session_id="session-1",
        agent="dialogue",
        lane="speech",
        action="SPEAK",
    )

    with pytest.raises(ValueError, match="SET_AMBIENCE"):
        AmbienceController().state_from_proposal(proposal)
