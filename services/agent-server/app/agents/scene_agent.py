from __future__ import annotations

from schemas import SessionState, StateUpdate

from .base import AgentResult, BaseAgent


class MockSceneAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="scene")

    def propose(self, state: SessionState) -> AgentResult:
        if state.scene.name != "default":
            return self.empty_result()

        update = StateUpdate(
            session_id=state.session_id,
            agent=self.name,
            patch={
                "scene": {
                    "name": "office_meeting",
                    "mood": "focused",
                    "ambience": "office_room_tone",
                    "metadata": {
                        "reverb": "small_room",
                    },
                }
            },
        )
        return AgentResult(
            state_updates=[update],
            metadata=self.make_metadata(trigger="default_scene"),
        )
