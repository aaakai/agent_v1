from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .sfx_dsl import SFXAssetQuery, SFXEvent


class SFXAsset(BaseModel):
    asset_id: str
    event: str
    path: str
    duration_ms: int
    tags: list[str]
    gain: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


DEFAULT_ASSETS = [
    SFXAsset(
        asset_id="door_knock_001",
        event="door_knock",
        path="mock://sfx/door_knock_001.wav",
        duration_ms=900,
        tags=["door", "knock", "indoor"],
        gain=0.5,
    ),
    SFXAsset(
        asset_id="footsteps_indoor_001",
        event="footsteps_indoor",
        path="mock://sfx/footsteps_indoor_001.wav",
        duration_ms=1800,
        tags=["footsteps", "indoor", "walk"],
        gain=0.45,
    ),
    SFXAsset(
        asset_id="cup_hit_001",
        event="cup_hit",
        path="mock://sfx/cup_hit_001.wav",
        duration_ms=500,
        tags=["cup", "hit", "table"],
        gain=0.4,
    ),
    SFXAsset(
        asset_id="rain_alley_loop",
        event="ambience",
        path="mock://ambience/rain_alley_loop.wav",
        duration_ms=60000,
        tags=["rain", "alley", "loop"],
        gain=0.3,
    ),
    SFXAsset(
        asset_id="office_room_tone",
        event="ambience",
        path="mock://ambience/office_room_tone.wav",
        duration_ms=60000,
        tags=["office", "room", "tone", "loop"],
        gain=0.18,
    ),
    SFXAsset(
        asset_id="spaceship_hum_loop",
        event="ambience",
        path="mock://ambience/spaceship_hum_loop.wav",
        duration_ms=60000,
        tags=["spaceship", "hum", "loop"],
        gain=0.22,
    ),
]


class MockSFXRetriever:
    def __init__(self, assets: list[SFXAsset] | None = None) -> None:
        self.assets = list(assets or DEFAULT_ASSETS)

    def retrieve(
        self,
        query: SFXAssetQuery | dict[str, Any],
        event: str | None = None,
    ) -> SFXAsset | None:
        parsed_query = (
            query if isinstance(query, SFXAssetQuery) else SFXAssetQuery.model_validate(query)
        )
        candidates = self.assets
        if event:
            candidates = [asset for asset in candidates if asset.event == event]
        elif parsed_query.tags:
            tags = set(parsed_query.tags)
            candidates = [
                asset for asset in candidates if tags.intersection(asset.tags)
            ]

        if parsed_query.duration_ms is not None:
            low, high = parsed_query.duration_ms
            candidates = [
                asset
                for asset in candidates
                if low <= asset.duration_ms <= high
            ]

        return candidates[0] if candidates else None

    def list_assets(self) -> list[SFXAsset]:
        return list(self.assets)

    def add_asset(self, asset: SFXAsset) -> None:
        self.assets.append(asset)

    def retrieve_for_event(self, sfx_event: SFXEvent) -> SFXAsset | None:
        return self.retrieve(sfx_event.asset_query, event=sfx_event.event)
