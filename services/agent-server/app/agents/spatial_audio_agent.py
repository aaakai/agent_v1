from __future__ import annotations

from typing import Any

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
        if proposal.lane.lower() != "sfx":
            return proposal

        metadata: dict[str, Any] = dict(proposal.metadata)
        metadata["spatial"] = {
            "azimuth_deg": -30,
            "elevation_deg": 0,
            "distance_m": 2.5,
            "reverb": state.scene.metadata.get("reverb", "small_room"),
        }
        return proposal.model_copy(update={"metadata": metadata}, deep=True)
