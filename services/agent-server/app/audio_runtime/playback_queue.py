from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlaybackQueueItem(BaseModel):
    command_id: str
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 50
    lane: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlaybackQueue:
    def __init__(self) -> None:
        self.items: list[PlaybackQueueItem] = []

    def push(self, item: PlaybackQueueItem) -> None:
        self.items.append(item)

    def pop_next(self) -> PlaybackQueueItem | None:
        if not self.items:
            return None
        index = max(range(len(self.items)), key=lambda idx: (self.items[idx].priority, -idx))
        return self.items.pop(index)

    def peek(self) -> PlaybackQueueItem | None:
        if not self.items:
            return None
        index = max(range(len(self.items)), key=lambda idx: (self.items[idx].priority, -idx))
        return self.items[index]

    def clear(self) -> None:
        self.items.clear()

    def __len__(self) -> int:
        return len(self.items)

    def to_list(self) -> list[dict[str, Any]]:
        return [item.model_dump(mode="python") for item in self.items]
