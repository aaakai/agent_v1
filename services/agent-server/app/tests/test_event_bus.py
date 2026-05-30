from __future__ import annotations

import asyncio

from realtime import EventBus
from schemas import Event
from schemas.event_types import ASR_FINAL, ASR_PARTIAL, USER_SPEECH_START


def test_subscribe_and_publish_calls_sync_handler() -> None:
    bus = EventBus()
    seen: list[Event] = []

    def handler(event: Event) -> None:
        seen.append(event)

    bus.subscribe(USER_SPEECH_START, handler)
    event = Event(session_id="session-1", type=USER_SPEECH_START)

    called = asyncio.run(bus.publish(event))

    assert called == 1
    assert seen == [event]


def test_publish_supports_async_handler() -> None:
    bus = EventBus()
    seen: list[str] = []

    async def handler(event: Event) -> None:
        await asyncio.sleep(0)
        seen.append(event.type)

    bus.subscribe(ASR_PARTIAL, handler)

    called = asyncio.run(
        bus.publish({"session_id": "session-1", "type": ASR_PARTIAL})
    )

    assert called == 1
    assert seen == [ASR_PARTIAL]


def test_publish_supports_wildcard_subscription() -> None:
    bus = EventBus()
    seen: list[str] = []

    def wildcard_handler(event: Event) -> None:
        seen.append(event.type)

    bus.subscribe("*", wildcard_handler)

    called = asyncio.run(bus.publish(Event(session_id="session-1", type=ASR_FINAL)))

    assert called == 1
    assert seen == [ASR_FINAL]


def test_unsubscribe_removes_handler() -> None:
    bus = EventBus()
    seen: list[Event] = []

    def handler(event: Event) -> None:
        seen.append(event)

    bus.subscribe(ASR_FINAL, handler)
    bus.unsubscribe(ASR_FINAL, handler)

    called = asyncio.run(bus.publish(Event(session_id="session-1", type=ASR_FINAL)))

    assert called == 0
    assert seen == []


def test_get_history_filters_by_session_id_and_event_type() -> None:
    bus = EventBus()
    event_1 = Event(session_id="session-1", type=ASR_PARTIAL)
    event_2 = Event(session_id="session-2", type=ASR_PARTIAL)
    event_3 = Event(session_id="session-1", type=ASR_FINAL)

    asyncio.run(bus.publish(event_1))
    asyncio.run(bus.publish(event_2))
    asyncio.run(bus.publish(event_3))

    assert bus.get_history(session_id="session-1") == [event_1, event_3]
    assert bus.get_history(event_type=ASR_PARTIAL) == [event_1, event_2]
