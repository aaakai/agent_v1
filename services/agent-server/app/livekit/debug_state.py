from __future__ import annotations

from time import time
from typing import Any

from pydantic import BaseModel, Field


def _now_ms() -> int:
    return int(time() * 1000)


class LiveKitDebugEvent(BaseModel):
    timestamp_ms: int = Field(default_factory=_now_ms)
    type: str
    message: str
    room_name: str | None = None
    participant_identity: str | None = None
    track_sid: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveKitDebugState(BaseModel):
    connected: bool = False
    room_name: str | None = None
    agent_identity: str | None = None
    participants: dict[str, Any] = Field(default_factory=dict)
    tracks: dict[str, Any] = Field(default_factory=dict)
    frames_received: int = 0
    last_frame_timestamp_ms: int | None = None
    events: list[LiveKitDebugEvent] = Field(default_factory=list)
    max_events: int = 200

    def append_event(self, event_type: str, message: str, **kwargs: Any) -> None:
        event = LiveKitDebugEvent(type=event_type, message=message, **kwargs)
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

    def mark_connected(self, room_name: str, agent_identity: str) -> None:
        self.connected = True
        self.room_name = room_name
        self.agent_identity = agent_identity
        self.append_event(
            "connected",
            f"agent connected to {room_name}",
            room_name=room_name,
            participant_identity=agent_identity,
        )

    def mark_disconnected(self, reason: str | None = None) -> None:
        self.connected = False
        self.append_event(
            "disconnected",
            reason or "agent disconnected",
            room_name=self.room_name,
            participant_identity=self.agent_identity,
        )

    def mark_participant_joined(
        self,
        identity: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.participants[identity] = dict(metadata or {})
        self.append_event(
            "participant_joined",
            f"participant joined: {identity}",
            room_name=self.room_name,
            participant_identity=identity,
            metadata=dict(metadata or {}),
        )

    def mark_track_subscribed(
        self,
        track_sid: str,
        participant_identity: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.tracks[track_sid] = {
            "participant_identity": participant_identity,
            "metadata": dict(metadata or {}),
        }
        self.append_event(
            "track_subscribed",
            f"audio track subscribed: {track_sid}",
            room_name=self.room_name,
            participant_identity=participant_identity,
            track_sid=track_sid,
            metadata=dict(metadata or {}),
        )

    def mark_frame_received(
        self,
        timestamp_ms: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.frames_received += 1
        self.last_frame_timestamp_ms = timestamp_ms
        self.append_event(
            "frame_received",
            "audio frame received",
            room_name=self.room_name,
            metadata=dict(metadata or {}),
        )

    def snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="python", exclude={"max_events"})

    def reset(self) -> None:
        self.connected = False
        self.room_name = None
        self.agent_identity = None
        self.participants = {}
        self.tracks = {}
        self.frames_received = 0
        self.last_frame_timestamp_ms = None
        self.events = []
