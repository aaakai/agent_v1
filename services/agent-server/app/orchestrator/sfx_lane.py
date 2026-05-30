from __future__ import annotations

from typing import Any

from schemas import OutputProposal, SessionState

from .priority_policy import effective_proposal_priority


def _priority(proposal: OutputProposal) -> int:
    return effective_proposal_priority(
        action=proposal.action,
        agent=proposal.agent,
        lane=proposal.lane,
        priority=proposal.priority,
        explicit_fields=proposal.model_fields_set,
    )


class SFXLane:
    def __init__(self) -> None:
        self.active: list[OutputProposal] = []

    def apply_proposal(
        self,
        proposal: OutputProposal,
        state: SessionState,
        now_ms: int,
    ) -> dict[str, Any]:
        priority = _priority(proposal)
        if proposal.lane.lower() != "sfx":
            return self._decision(
                decision="reject",
                reason="proposal_not_for_sfx_lane",
                proposal=proposal,
                priority=priority,
                duck=False,
                now_ms=now_ms,
            )
        if proposal.action.upper() != "PLAY_SFX":
            return self._decision(
                decision="reject",
                reason="unsupported_sfx_action",
                proposal=proposal,
                priority=priority,
                duck=False,
                now_ms=now_ms,
            )

        duck = state.assistant.is_speaking or state.audio_runtime.speech_lane_busy
        self.active.append(proposal)
        state.audio_runtime.sfx_playing.append(proposal.model_dump(mode="python"))
        return self._decision(
            decision="play",
            reason="sfx_allowed",
            proposal=proposal,
            priority=priority,
            duck=duck,
            now_ms=now_ms,
        )

    def duck_all(self, reason: str) -> dict[str, Any]:
        return {
            "decision": "duck",
            "lane": "sfx",
            "reason": reason,
            "priority": None,
            "duck": True,
            "active_count": len(self.active),
            "proposal_ids": [proposal.proposal_id for proposal in self.active],
        }

    def stop_all(self, reason: str) -> dict[str, Any]:
        stopped = [proposal.model_dump(mode="python") for proposal in self.active]
        self.active.clear()
        return {
            "decision": "stop",
            "lane": "sfx",
            "reason": reason,
            "priority": None,
            "duck": False,
            "stopped": stopped,
        }

    def _decision(
        self,
        decision: str,
        reason: str,
        proposal: OutputProposal,
        priority: int,
        duck: bool,
        now_ms: int,
    ) -> dict[str, Any]:
        return {
            "decision": decision,
            "lane": "sfx",
            "reason": reason,
            "proposal_id": proposal.proposal_id,
            "priority": priority,
            "duck": duck,
            "now_ms": now_ms,
        }
