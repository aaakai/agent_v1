from __future__ import annotations

from .player_protocol import PlayerCommand, commands_from_decisions
from .player_sink import BasePlayerCommandSink, InMemoryPlayerSink


class CommandRecorder:
    def __init__(self, sink: BasePlayerCommandSink | None = None) -> None:
        self.sink = sink or InMemoryPlayerSink()

    def decisions_to_commands(
        self,
        decisions: list[dict[str, object]],
    ) -> list[PlayerCommand]:
        return commands_from_decisions(decisions)

    async def record_decisions(
        self,
        decisions: list[dict[str, object]],
    ) -> list[PlayerCommand]:
        commands = self.decisions_to_commands(decisions)
        await self.sink.send_many(commands)
        return commands

    async def record_command(self, command: PlayerCommand) -> None:
        await self.sink.send(command)

    def get_commands(self) -> list[PlayerCommand]:
        return self.sink.get_sent_commands()

    def clear(self) -> None:
        clear = getattr(self.sink, "clear", None)
        if callable(clear):
            clear()
