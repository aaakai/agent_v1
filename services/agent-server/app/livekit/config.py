from __future__ import annotations

import os

from pydantic import BaseModel


class LiveKitConfig(BaseModel):
    url: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    room_name: str | None = None
    agent_identity: str = "lulula-agent"

    @classmethod
    def from_env(cls) -> "LiveKitConfig":
        return cls(
            url=os.getenv("LIVEKIT_URL"),
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET"),
            room_name=os.getenv("LIVEKIT_ROOM"),
            agent_identity=os.getenv("LIVEKIT_AGENT_IDENTITY") or "lulula-agent",
        )

    def is_configured(self) -> bool:
        return not self.missing_fields()

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.url:
            missing.append("url")
        if not self.api_key:
            missing.append("api_key")
        if not self.api_secret:
            missing.append("api_secret")
        return missing

    def default_room_name(self) -> str:
        return self.room_name or "lulula-dev-room"

    def to_safe_dict(self) -> dict[str, str | None | bool]:
        return {
            "url": self.url,
            "api_key": self.api_key,
            "api_secret": "***" if self.api_secret else None,
            "room_name": self.default_room_name(),
            "agent_identity": self.agent_identity or "lulula-agent",
            "configured": self.is_configured(),
        }
