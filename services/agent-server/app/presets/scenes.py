from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScenePreset(BaseModel):
    name: str
    mood: str
    ambience: str
    reverb: str
    metadata: dict[str, Any] = Field(default_factory=dict)


SCENE_PRESETS: dict[str, ScenePreset] = {
    "office_meeting": ScenePreset(
        name="office_meeting",
        mood="focused",
        ambience="office_room_tone",
        reverb="small_room",
        metadata={
            "room_size": "small",
            "default_sfx_gain": 0.45,
            "default_ambience_gain": 0.18,
        },
    ),
    "rainy_alley": ScenePreset(
        name="rainy_alley",
        mood="tense",
        ambience="rain_alley_loop",
        reverb="wet_alley",
        metadata={
            "room_size": "open_narrow",
            "default_sfx_gain": 0.55,
            "default_ambience_gain": 0.25,
        },
    ),
    "spaceship_cabin": ScenePreset(
        name="spaceship_cabin",
        mood="sci_fi",
        ambience="spaceship_hum_loop",
        reverb="metal_cabin",
        metadata={
            "room_size": "medium",
            "default_sfx_gain": 0.5,
            "default_ambience_gain": 0.22,
        },
    ),
}


def get_scene_preset(name: str) -> ScenePreset | None:
    return SCENE_PRESETS.get(name)


def list_scene_presets() -> list[ScenePreset]:
    return list(SCENE_PRESETS.values())


def default_scene_preset() -> ScenePreset:
    return SCENE_PRESETS["office_meeting"]
