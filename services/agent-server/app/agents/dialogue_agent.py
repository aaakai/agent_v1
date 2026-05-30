from __future__ import annotations

from schemas import OutputProposal, SessionState

from .base import AgentResult, BaseAgent


class MockDialogueAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="dialogue")

    def propose(self, state: SessionState) -> AgentResult:
        if state.user_audio.is_speaking:
            return self.empty_result()

        if state.metadata.get("interrupt_reason") == "dangerous_operation":
            return AgentResult(
                proposals=[
                    OutputProposal(
                        session_id=state.session_id,
                        agent=self.name,
                        lane="speech",
                        action="SPEAK",
                        text="这个操作风险很高。我们先确认备份、影响范围和回滚方案。",
                        priority=60,
                        timing={"start_when": "user_turn_end"},
                        interrupt_policy={"interruptible_by_user": True},
                        mixing={"gain": 0.75, "duck_others": True},
                    )
                ],
                metadata=self.make_metadata(trigger="interrupt_followup"),
            )

        if not state.asr.final:
            return self.empty_result()

        proposal = OutputProposal(
            session_id=state.session_id,
            agent=self.name,
            lane="speech",
            action="SPEAK",
            text="我建议把这个系统拆成输入、决策、调度和音频渲染四层。",
            priority=50,
            timing={"start_when": "user_turn_end"},
            interrupt_policy={"interruptible_by_user": True},
            mixing={
                "gain": 0.75,
                "duck_others": True,
            },
        )
        return AgentResult(
            proposals=[proposal],
            metadata=self.make_metadata(trigger="asr_final"),
        )
