from __future__ import annotations

import asyncio
import json

from audio_runtime import (
    MockWebSocketConnection,
    MockWebSocketPlayerSink,
    PlayerCommand,
)


def test_mock_websocket_player_sink_sends_json_message() -> None:
    sink = MockWebSocketPlayerSink()
    command = PlayerCommand(session_id="s1", type="PLAY_SFX")

    asyncio.run(sink.send(command))

    messages = sink.get_sent_messages()
    assert len(messages) == 1
    assert json.loads(messages[0])["type"] == "PLAY_SFX"
    assert sink.get_sent_commands()[0]["session_id"] == "s1"


def test_mock_websocket_player_sink_send_many_and_close() -> None:
    connection = MockWebSocketConnection()
    sink = MockWebSocketPlayerSink(connection)

    asyncio.run(
        sink.send_many(
            [
                PlayerCommand(session_id="s1", type="PLAY_SFX"),
                PlayerCommand(session_id="s1", type="STOP_TTS"),
            ]
        )
    )
    asyncio.run(sink.close())

    assert [json.loads(message)["type"] for message in sink.get_sent_messages()] == [
        "PLAY_SFX",
        "STOP_TTS",
    ]
    assert connection.closed is True
