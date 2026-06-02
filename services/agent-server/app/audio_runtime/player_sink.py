from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .player_protocol import PlayerCommand, command_to_dict


class BasePlayerCommandSink:
    async def send(self, command: PlayerCommand) -> None:
        raise NotImplementedError

    async def send_many(self, commands: list[PlayerCommand]) -> None:
        for command in commands:
            await self.send(command)

    async def close(self) -> None:
        return None

    def get_sent_commands(self) -> list[PlayerCommand]:
        return []


class InMemoryPlayerSink(BasePlayerCommandSink):
    def __init__(self) -> None:
        self.commands: list[PlayerCommand] = []
        self.closed = False

    async def send(self, command: PlayerCommand) -> None:
        self._ensure_open()
        self.commands.append(command)

    async def send_many(self, commands: list[PlayerCommand]) -> None:
        self._ensure_open()
        self.commands.extend(commands)

    async def close(self) -> None:
        self.closed = True

    def get_sent_commands(self) -> list[PlayerCommand]:
        return list(self.commands)

    def clear(self) -> None:
        self.commands.clear()

    def _ensure_open(self) -> None:
        if self.closed:
            raise RuntimeError("sink is closed")


class JSONLPlayerSink(BasePlayerCommandSink):
    def __init__(self, path: str | Path, append: bool = True) -> None:
        self.path = Path(path)
        self.append = append
        self.commands: list[PlayerCommand] = []
        self.closed = False
        self._initialized = False

    async def send(self, command: PlayerCommand) -> None:
        await self.send_many([command])

    async def send_many(self, commands: list[PlayerCommand]) -> None:
        self._ensure_open()
        if not commands:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if self.append or self._initialized else "w"
        with self.path.open(mode, encoding="utf-8") as file:
            for command in commands:
                file.write(
                    json.dumps(command_to_dict(command), ensure_ascii=False) + "\n"
                )
        self.commands.extend(commands)
        self._initialized = True

    async def close(self) -> None:
        self.closed = True

    def get_sent_commands(self) -> list[PlayerCommand]:
        return list(self.commands)

    def _ensure_open(self) -> None:
        if self.closed:
            raise RuntimeError("sink is closed")


def command_to_json_dict(command: PlayerCommand) -> dict[str, Any]:
    return command_to_dict(command)
