from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from presets import default_scene_preset, get_scene_preset
from schemas import OutputProposal


class AmbienceState(BaseModel):
    scene: str
    asset: str
    gain: float
    loop: bool = True
    fade_ms: int = 1200
    reverb: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AmbienceController:
    def ambience_for_scene(self, session_id: str, scene_name: str) -> OutputProposal:
        preset = get_scene_preset(scene_name) or default_scene_preset()
        gain = preset.metadata.get("default_ambience_gain", 0.18)
        return OutputProposal(
            session_id=session_id,
            agent="ambience_controller",
            lane="ambience",
            action="SET_AMBIENCE",
            text=preset.ambience,
            priority=10,
            metadata={
                "scene": preset.name,
                "ambience": preset.ambience,
                "asset": preset.ambience,
                "reverb": preset.reverb,
            },
            mixing={
                "gain": gain,
                "loop": True,
                "fade_ms": 1200,
            },
        )

    def state_from_proposal(self, proposal: OutputProposal) -> AmbienceState:
        if proposal.lane.lower() != "ambience" or proposal.action.upper() != "SET_AMBIENCE":
            raise ValueError("proposal must be a SET_AMBIENCE proposal on the ambience lane")
        return AmbienceState(
            scene=proposal.metadata.get("scene", "default"),
            asset=proposal.metadata.get(
                "asset",
                proposal.metadata.get("ambience", proposal.text or ""),
            ),
            gain=proposal.mixing.get("gain", 0.18),
            loop=proposal.mixing.get("loop", True),
            fade_ms=proposal.mixing.get("fade_ms", 1200),
            reverb=proposal.metadata.get("reverb"),
            metadata={
                key: value
                for key, value in proposal.metadata.items()
                if key not in {"scene", "asset", "ambience", "reverb"}
            },
        )
