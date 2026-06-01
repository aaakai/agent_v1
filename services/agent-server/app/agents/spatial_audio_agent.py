from __future__ import annotations

from audio_runtime import attach_spatial_to_proposal
from presets import get_scene_preset
from schemas import OutputProposal, SessionState

from .base import BaseAgent


class MockSpatialAudioAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="spatial_audio")

    def enhance_sfx_proposal(
        self,
        proposal: OutputProposal,
        state: SessionState,
    ) -> OutputProposal:
        enhanced = attach_spatial_to_proposal(proposal, scene_name=state.scene.name)
        if (
            enhanced is not proposal
            and get_scene_preset(state.scene.name) is None
            and state.scene.metadata.get("reverb")
        ):
            metadata = dict(enhanced.metadata)
            spatial = dict(metadata.get("spatial", {}))
            spatial["reverb"] = state.scene.metadata["reverb"]
            metadata["spatial"] = spatial
            return enhanced.model_copy(update={"metadata": metadata}, deep=True)
        return enhanced
