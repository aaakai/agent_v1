from __future__ import annotations

from schemas import OutputProposal, SessionState

from .base import AgentResult, BaseAgent


SFX_KEYWORDS = ("敲门", "门响", "knock", "door")


class MockSFXPlannerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="sfx_planner")

    def propose(self, state: SessionState) -> AgentResult:
        text_source = state.asr.final or state.asr.partial
        if not text_source:
            return self.empty_result()

        normalized_text = text_source.lower()
        if not any(
            keyword in text_source or keyword.lower() in normalized_text
            for keyword in SFX_KEYWORDS
        ):
            return self.empty_result()

        proposal = OutputProposal(
            session_id=state.session_id,
            agent=self.name,
            lane="sfx",
            action="PLAY_SFX",
            priority=20,
            timing={"start_after_ms": 300},
            mixing={
                "gain": 0.55,
                "duck_under_speech": True,
            },
            metadata={
                "event": "door_knock",
                "asset_query": {
                    "tags": ["door", "knock", "indoor"],
                    "duration_ms": [300, 1200],
                },
            },
        )
        return AgentResult(
            proposals=[proposal],
            metadata=self.make_metadata(trigger="door_knock_keyword"),
        )
