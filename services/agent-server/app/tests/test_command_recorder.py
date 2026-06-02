from __future__ import annotations

import asyncio

from audio_runtime import CommandRecorder, InMemoryPlayerSink


def test_command_recorder_converts_supported_decisions() -> None:
    recorder = CommandRecorder()
    commands = recorder.decisions_to_commands(
        [
            {"session_id": "s1", "decision": "play", "lane": "sfx"},
            {
                "session_id": "s1",
                "decision": "play",
                "lane": "speech",
                "proposal_action": "BACKCHANNEL",
            },
            {"session_id": "s1", "decision": "stop", "lane": "speech"},
            {"session_id": "s1", "decision": "duck", "lane": "ambience"},
        ]
    )

    assert [command.type for command in commands] == [
        "PLAY_SFX",
        "PLAY_BACKCHANNEL",
        "STOP_TTS",
        "DUCK_AUDIO",
    ]


def test_command_recorder_filters_unknown_and_records_to_sink() -> None:
    sink = InMemoryPlayerSink()
    recorder = CommandRecorder(sink=sink)

    commands = asyncio.run(
        recorder.record_decisions(
            [
                {"session_id": "s1", "decision": "unknown", "lane": "sfx"},
                {"session_id": "s1", "decision": "play", "lane": "sfx"},
            ]
        )
    )

    assert [command.type for command in commands] == ["PLAY_SFX"]
    assert [command.type for command in recorder.get_commands()] == ["PLAY_SFX"]

    recorder.clear()
    assert recorder.get_commands() == []
