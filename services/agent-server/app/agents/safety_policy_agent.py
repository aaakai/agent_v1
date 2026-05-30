from __future__ import annotations

from schemas import OutputProposal, SessionState

from .base import BaseAgent


class SafetyPolicyAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="safety_policy")

    def validate_proposal(
        self,
        proposal: OutputProposal,
        state: SessionState,
    ) -> tuple[bool, str]:
        lane = proposal.lane.lower()
        action = proposal.action.upper()

        if action == "BACKCHANNEL" and state.assistant.is_speaking:
            return False, "assistant_speaking_blocks_backchannel"

        if (
            lane == "speech"
            and action == "SPEAK"
            and state.user_audio.is_speaking
            and proposal.priority < 90
        ):
            return False, "user_speaking_blocks_low_priority_speech"

        if lane == "sfx" and proposal.mixing.get("gain", 0.0) > 0.8:
            return False, "sfx_gain_too_high"

        return True, "allowed"
