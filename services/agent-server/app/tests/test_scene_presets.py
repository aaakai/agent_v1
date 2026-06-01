from __future__ import annotations

from presets import default_scene_preset, get_scene_preset, list_scene_presets


def test_scene_presets_are_available() -> None:
    assert get_scene_preset("office_meeting").ambience == "office_room_tone"
    assert get_scene_preset("rainy_alley").reverb == "wet_alley"
    assert get_scene_preset("spaceship_cabin").mood == "sci_fi"


def test_unknown_scene_returns_none() -> None:
    assert get_scene_preset("unknown") is None


def test_default_scene_is_office_meeting() -> None:
    assert default_scene_preset().name == "office_meeting"


def test_list_scene_presets_contains_defaults() -> None:
    names = {preset.name for preset in list_scene_presets()}

    assert {"office_meeting", "rainy_alley", "spaceship_cabin"}.issubset(names)
