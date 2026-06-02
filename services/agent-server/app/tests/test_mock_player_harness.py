from __future__ import annotations

import asyncio

from audio_runtime import PlayerCommand
from audio_runtime.mock_player import MockPlayerHarness


def test_mock_player_harness_run_commands_consumes_sfx_and_ambience() -> None:
    harness = MockPlayerHarness()

    result = harness.run_commands(
        [
            PlayerCommand(session_id="s1", type="PLAY_SFX", payload={"event": "door"}),
            PlayerCommand(
                session_id="s1",
                type="SET_AMBIENCE",
                payload={"asset": "office_room_tone"},
            ),
        ]
    )

    state = result["playback_state"]
    assert result["commands_applied"] == 2
    assert state["sfx"]["active"][0]["payload"]["event"] == "door"
    assert state["ambience"]["current"]["payload"]["asset"] == "office_room_tone"


def test_mock_player_harness_debug_sfx_scenario_sets_sfx_active() -> None:
    harness = MockPlayerHarness()

    result = asyncio.run(harness.run_debug_scenario("sfx"))

    assert result["commands_applied"] > 0
    assert result["playback_state"]["sfx"]["active"]


def test_mock_player_harness_debug_backchannel_scenario_updates_speech() -> None:
    harness = MockPlayerHarness()

    result = asyncio.run(harness.run_debug_scenario("backchannel"))

    assert result["playback_state"]["history"]
    assert (
        result["playback_state"]["speech"]["current"] is not None
        or result["playback_state"]["speech"]["queue"]
    )


def test_mock_player_harness_debug_full_scenario_runs() -> None:
    harness = MockPlayerHarness()

    result = asyncio.run(harness.run_debug_scenario("full"))

    assert result["scenario"] == "full"
    assert result["commands_applied"] == len(result["player_commands"])


def test_mock_player_harness_debug_ambience_scenario_sets_ambience() -> None:
    harness = MockPlayerHarness()

    result = asyncio.run(harness.run_debug_scenario("ambience"))

    assert result["playback_state"]["ambience"]["current"] is not None
