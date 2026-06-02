from __future__ import annotations

import json

from .player_protocol import PlayerCommand, command_to_dict
from .player_sink import BasePlayerCommandSink


class MockWebSocketConnection:
    def __init__(self) -> None:
        self.sent_messages: list[str] = []
        self.closed = False

    async def send_text(self, text: str) -> None:
        if self.closed:
            raise RuntimeError("websocket connection is closed")
        self.sent_messages.append(text)

    async def close(self) -> None:
        self.closed = True


class MockWebSocketPlayerSink(BasePlayerCommandSink):
    def __init__(self, connection: MockWebSocketConnection | None = None) -> None:
        self.connection = connection or MockWebSocketConnection()

    async def send(self, command: PlayerCommand) -> None:
        await self.connection.send_text(
            json.dumps(command_to_dict(command), ensure_ascii=False)
        )

    async def send_many(self, commands: list[PlayerCommand]) -> None:
        for command in commands:
            await self.send(command)

    async def close(self) -> None:
        await self.connection.close()

    def get_sent_messages(self) -> list[str]:
        return list(self.connection.sent_messages)

    def get_sent_commands(self) -> list[dict[str, object]]:  # type: ignore[override]
        return [json.loads(message) for message in self.connection.sent_messages]
