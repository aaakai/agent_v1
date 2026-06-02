from __future__ import annotations

import asyncio
import json

import pytest

from audio_runtime import InMemoryPlayerSink, JSONLPlayerSink, PlayerCommand


def test_in_memory_player_sink_send_many_close_and_clear() -> None:
    sink = InMemoryPlayerSink()
    command = PlayerCommand(session_id="s1", type="PLAY_SFX")
    second = PlayerCommand(session_id="s1", type="DUCK_AUDIO")

    asyncio.run(sink.send(command))
    asyncio.run(sink.send_many([second]))

    assert [item.type for item in sink.get_sent_commands()] == [
        "PLAY_SFX",
        "DUCK_AUDIO",
    ]

    sink.clear()
    assert sink.get_sent_commands() == []

    asyncio.run(sink.close())
    assert sink.closed is True
    with pytest.raises(RuntimeError, match="sink is closed"):
        asyncio.run(sink.send(command))


def test_jsonl_player_sink_writes_json_lines(tmp_path) -> None:
    path = tmp_path / "commands" / "player.jsonl"
    sink = JSONLPlayerSink(path)
    command = PlayerCommand(
        session_id="s1",
        type="PLAY_BACKCHANNEL",
        payload={"text": "嗯"},
    )

    asyncio.run(sink.send(command))

    assert path.exists()
    line = path.read_text(encoding="utf-8").splitlines()[0]
    payload = json.loads(line)
    assert payload["type"] == "PLAY_BACKCHANNEL"
    assert payload["payload"]["text"] == "嗯"
    assert "\\u" not in line
    assert sink.get_sent_commands()[0].command_id == command.command_id


def test_jsonl_player_sink_send_many_and_overwrite(tmp_path) -> None:
    path = tmp_path / "player.jsonl"
    path.write_text('{"old": true}\n', encoding="utf-8")
    sink = JSONLPlayerSink(path, append=False)

    asyncio.run(
        sink.send_many(
            [
                PlayerCommand(session_id="s1", type="PLAY_SFX"),
                PlayerCommand(session_id="s1", type="STOP_TTS"),
            ]
        )
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["type"] == "PLAY_SFX"
    assert json.loads(lines[1])["type"] == "STOP_TTS"
