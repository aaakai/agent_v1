from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from .audio_frame import AudioFrame
from .audio_ring_buffer import AudioRingBuffer

AudioConsumer = Callable[[AudioFrame], Any | Awaitable[Any]]


class RawAudioRouter:
    def __init__(self, ring_buffer: AudioRingBuffer | None = None) -> None:
        self.consumers: dict[str, AudioConsumer] = {}
        self.ring_buffer = ring_buffer or AudioRingBuffer()
        self.routed_count = 0

    def add_consumer(self, name: str, consumer: AudioConsumer) -> None:
        if not name or not name.strip():
            raise ValueError("consumer name must not be empty")
        self.consumers[name] = consumer

    def remove_consumer(self, name: str) -> None:
        self.consumers.pop(name, None)

    async def route(self, frame: AudioFrame) -> dict[str, Any]:
        self.ring_buffer.append(frame)
        self.routed_count += 1

        async def call_consumer(name: str, consumer: AudioConsumer) -> dict[str, str] | None:
            try:
                if inspect.iscoroutinefunction(consumer):
                    result = consumer(frame)
                else:
                    result = await asyncio.to_thread(consumer, frame)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:  # noqa: BLE001 - route must isolate consumers.
                return {"consumer": name, "error": str(exc)}
            return None

        results = await asyncio.gather(
            *[
                call_consumer(name, consumer)
                for name, consumer in list(self.consumers.items())
            ]
        )
        errors = [result for result in results if result is not None]
        return {
            "frame_id": frame.frame_id,
            "consumer_count": len(self.consumers),
            "errors": errors,
        }

    def get_consumer_names(self) -> list[str]:
        return list(self.consumers.keys())

    def get_recent_frames(self, count: int | None = None) -> list[AudioFrame]:
        return self.ring_buffer.get_recent(count)
