from __future__ import annotations

from schemas import OutputProposal, SessionState

from .base import AgentResult, BaseAgent


class MockBackchannelAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="backchannel")

    def propose(self, state: SessionState) -> AgentResult:
        if not state.user_audio.is_speaking:
            return self.empty_result()
        if state.user_audio.backchannel_opportunity < 0.75:
            return self.empty_result()
        if state.assistant.is_speaking or state.audio_runtime.speech_lane_busy:
            return self.empty_result()

        proposal = OutputProposal(
            session_id=state.session_id,
            agent=self.name,
            lane="speech",
            action="BACKCHANNEL",
            text="嗯，我懂",
            priority=30,
            timing={
                "start_after_ms": 80,
                "max_duration_ms": 600,
            },
            interrupt_policy={
                "can_interrupt_user": False,
                "can_interrupt_assistant": False,
            },
            mixing={"gain": 0.35},
        )
        return AgentResult(
            proposals=[proposal],
            metadata=self.make_metadata(trigger="backchannel_opportunity"),
        )
