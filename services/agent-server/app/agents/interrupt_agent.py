from __future__ import annotations

from schemas import ControlAction, SessionState

from .base import AgentResult, BaseAgent


DANGEROUS_KEYWORDS = (
    "删库",
    "删除生产库",
    "生产库删",
    "drop database",
    "delete production",
    "发 API key",
    "泄露密钥",
)

FACT_ERROR_KEYWORDS = (
    "一加一等于三",
    "1+1=3",
    "1 加 1 等于 3",
)


class MockInterruptAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="interrupt")

    def propose(self, state: SessionState) -> AgentResult:
        if (
            (state.assistant.is_speaking or state.audio_runtime.speech_lane_busy)
            and state.user_audio.is_speaking
            and state.user_audio.barge_in_score >= 0.6
        ):
            barge_in_score = state.user_audio.barge_in_score
            return AgentResult(
                control_actions=[
                    ControlAction(
                        session_id=state.session_id,
                        agent=self.name,
                        action="STOP_SPEAKING",
                        priority=95,
                        reason="user_barge_in",
                        target="speech_lane",
                        payload={
                            "audio_triggered": True,
                            "barge_in_score": barge_in_score,
                        },
                    )
                ],
                metadata=self.make_metadata(trigger="user_barge_in"),
            )

        partial = state.asr.partial or ""
        normalized_partial = partial.lower()
        if (
            self._contains_keyword(partial, normalized_partial, DANGEROUS_KEYWORDS)
            and not self._dangerous_followup_already_tracked(state)
        ):
            return AgentResult(
                control_actions=[
                    ControlAction(
                        session_id=state.session_id,
                        agent=self.name,
                        action="INTERRUPT_USER",
                        priority=95,
                        reason="dangerous_operation",
                        target="user",
                        payload={
                            "semantic_triggered": True,
                            "interrupt_phrase": "等一下，先别操作。",
                            "followup_needed": True,
                            "followup_policy": "dialogue_explain_if_user_pauses",
                            "audio_context": self._audio_context(state),
                        },
                    )
                ],
                metadata=self.make_metadata(trigger="dangerous_operation"),
            )

        if self._contains_keyword(partial, normalized_partial, FACT_ERROR_KEYWORDS):
            return AgentResult(
                control_actions=[
                    ControlAction(
                        session_id=state.session_id,
                        agent=self.name,
                        action="INTERRUPT_USER",
                        priority=85,
                        reason="obvious_factual_error",
                        target="user",
                        payload={
                            "semantic_triggered": True,
                            "interrupt_phrase": "等一下，一加一是二。",
                            "followup_needed": False,
                            "audio_context": self._audio_context(state),
                        },
                    )
                ],
                metadata=self.make_metadata(trigger="obvious_factual_error"),
            )

        if state.user_audio.is_speaking:
            return AgentResult(
                control_actions=[
                    ControlAction(
                        session_id=state.session_id,
                        agent=self.name,
                        action="ALLOW_USER_CONTINUE",
                        priority=0,
                        reason="user_is_still_speaking",
                    )
                ],
                metadata=self.make_metadata(trigger="user_is_still_speaking"),
            )

        return self.empty_result()

    def _contains_keyword(
        self,
        raw_text: str,
        normalized_text: str,
        keywords: tuple[str, ...],
    ) -> bool:
        return any(
            keyword in raw_text or keyword.lower() in normalized_text
            for keyword in keywords
        )

    def _audio_context(self, state: SessionState) -> dict:
        return {
            "is_speaking": state.user_audio.is_speaking,
            "energy": state.user_audio.energy,
            "pause_ms": state.user_audio.pause_ms,
            "barge_in_score": state.user_audio.barge_in_score,
            "assistant_speaking": state.assistant.is_speaking,
            "speech_lane_busy": state.audio_runtime.speech_lane_busy,
        }

    def _dangerous_followup_already_tracked(self, state: SessionState) -> bool:
        return (
            state.metadata.get("interrupt_reason") == "dangerous_operation"
            and state.metadata.get("followup_needed") is True
        )
