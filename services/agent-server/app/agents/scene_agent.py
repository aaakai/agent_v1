from __future__ import annotations

from presets import default_scene_preset
from schemas import SessionState, StateUpdate

from .base import AgentResult, BaseAgent


class MockSceneAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="scene")

    def propose(self, state: SessionState) -> AgentResult:
        if state.scene.name != "default":
            return self.empty_result()

        preset = default_scene_preset()
        update = StateUpdate(
            session_id=state.session_id,
            agent=self.name,
            patch={
                "scene": {
                    "name": preset.name,
                    "mood": preset.mood,
                    "ambience": preset.ambience,
                    "metadata": {
                        "reverb": preset.reverb,
                    },
                }
            },
        )
        return AgentResult(
            state_updates=[update],
            metadata=self.make_metadata(trigger="default_scene"),
        )
