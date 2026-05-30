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


class AmbienceLane:
    def __init__(self) -> None:
        self.current: OutputProposal | None = None

    def apply_proposal(
        self,
        proposal: OutputProposal,
        state: SessionState,
        now_ms: int,
    ) -> dict[str, Any]:
        priority = _priority(proposal)
        if proposal.lane.lower() != "ambience":
            return self._decision(
                decision="reject",
                reason="proposal_not_for_ambience_lane",
                proposal=proposal,
                priority=priority,
                duck=False,
                now_ms=now_ms,
                replaced=None,
            )
        if proposal.action.upper() != "SET_AMBIENCE":
            return self._decision(
                decision="reject",
                reason="unsupported_ambience_action",
                proposal=proposal,
                priority=priority,
                duck=False,
                now_ms=now_ms,
                replaced=None,
            )

        replaced = self.current
        self.current = proposal
        state.audio_runtime.ambience_playing = proposal.proposal_id
        if proposal.text is not None:
            state.scene.ambience = proposal.text
        duck = state.assistant.is_speaking or state.audio_runtime.speech_lane_busy
        return self._decision(
            decision="replace" if replaced else "play",
            reason="ambience_replaced" if replaced else "ambience_set",
            proposal=proposal,
            priority=priority,
            duck=duck,
            now_ms=now_ms,
            replaced=replaced,
        )

    def duck(self, reason: str) -> dict[str, Any]:
        return {
            "decision": "duck",
            "lane": "ambience",
            "reason": reason,
            "proposal_id": self.current.proposal_id if self.current else None,
            "priority": _priority(self.current) if self.current else None,
            "duck": True,
        }

    def stop(self, reason: str) -> dict[str, Any]:
        stopped = self.current
        self.current = None
        return {
            "decision": "stop",
            "lane": "ambience",
            "reason": reason,
            "proposal_id": stopped.proposal_id if stopped else None,
            "priority": _priority(stopped) if stopped else None,
            "duck": False,
            "stopped": stopped.model_dump(mode="python") if stopped else None,
        }

    def _decision(
        self,
        decision: str,
        reason: str,
        proposal: OutputProposal,
        priority: int,
        duck: bool,
        now_ms: int,
        replaced: OutputProposal | None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "decision": decision,
            "lane": "ambience",
            "reason": reason,
            "proposal_id": proposal.proposal_id,
            "priority": priority,
            "duck": duck,
            "now_ms": now_ms,
        }
        if replaced is not None:
            result["replaced"] = replaced.model_dump(mode="python")
        return result
