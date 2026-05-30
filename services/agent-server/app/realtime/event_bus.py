from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from schemas import Event

EventHandler = Callable[[Event], Any | Awaitable[Any]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self.history: list[Event] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if not event_type or not event_type.strip():
            raise ValueError("event_type must not be empty")
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._subscribers.get(event_type)
        if not handlers:
            return
        if handler in handlers:
            handlers.remove(handler)
        if not handlers:
            self._subscribers.pop(event_type, None)

    async def publish(self, event: Event | Mapping[str, Any]) -> int:
        normalized = event if isinstance(event, Event) else Event.model_validate(event)
        self.history.append(normalized)

        handlers = [
            *self._subscribers.get(normalized.type, []),
            *self._subscribers.get("*", []),
        ]
        for handler in handlers:
            result = handler(normalized)
            if inspect.isawaitable(result):
                await result
        return len(handlers)

    def get_history(
        self,
        session_id: str | None = None,
        event_type: str | None = None,
    ) -> list[Event]:
        events = self.history
        if session_id is not None:
            events = [event for event in events if event.session_id == session_id]
        if event_type is not None:
            events = [event for event in events if event.type == event_type]
        return list(events)
