from __future__ import annotations

from typing import Any

from schemas import ControlAction, OutputProposal, SessionState

from .priority_policy import (
    PriorityPolicy,
    effective_control_priority,
    effective_proposal_priority,
)


def _proposal_priority(proposal: OutputProposal) -> int:
    return effective_proposal_priority(
        action=proposal.action,
        agent=proposal.agent,
        lane=proposal.lane,
        priority=proposal.priority,
        explicit_fields=proposal.model_fields_set,
    )


def _control_priority(action: ControlAction) -> int:
    return effective_control_priority(
        action=action.action,
        agent=action.agent,
        priority=action.priority,
        explicit_fields=action.model_fields_set,
    )


def _proposal_payload(proposal: OutputProposal | None) -> dict[str, Any] | None:
    if proposal is None:
        return None
    return proposal.model_dump(mode="python")


class SpeechLane:
    def __init__(self, cooldown_ms: int = 3000) -> None:
        self.current: OutputProposal | None = None
        self.queue: list[OutputProposal] = []
        self.last_backchannel_at_ms: int | None = None
        self.cooldown_ms = cooldown_ms
        self.priority_policy = PriorityPolicy()

    def can_play(
        self,
        proposal: OutputProposal,
        state: SessionState,
        now_ms: int,
    ) -> tuple[bool, str]:
        if proposal.lane.lower() != "speech":
            return False, "proposal_not_for_speech_lane"

        action = proposal.action.upper()
        speech_busy = self._speech_busy(state)

        if self._is_interrupt(proposal):
            return True, "interrupt_can_play"

        if action == "BACKCHANNEL":
            if not state.user_audio.is_speaking:
                return False, "user_not_speaking"
            if speech_busy:
                return False, "speech_lane_busy"
            if self._backchannel_in_cooldown(now_ms):
                return False, "backchannel_cooldown"
            return True, "backchannel_allowed"

        if action == "SPEAK":
            if self._is_dialogue(proposal) and state.user_audio.is_speaking:
                return False, "user_speaking_queue_dialogue"
            if speech_busy:
                return False, "speech_lane_busy"
            return True, "speech_allowed"

        return False, "unsupported_speech_action"

    def apply_proposal(
        self,
        proposal: OutputProposal,
        state: SessionState,
        now_ms: int,
    ) -> dict[str, Any]:
        priority = _proposal_priority(proposal)
        if proposal.lane.lower() != "speech":
            return self._decision(
                decision="reject",
                reason="proposal_not_for_speech_lane",
                proposal=proposal,
                priority=priority,
            )

        if self._is_interrupt(proposal) and self._speech_busy(state):
            preempted = self.current
            self._play(proposal, state)
            return self._decision(
                decision="preempt",
                reason="interrupt_preempted_current_speech",
                proposal=proposal,
                priority=priority,
                preempted=preempted,
            )

        can_play, reason = self.can_play(proposal, state, now_ms)
        if can_play:
            self._play(proposal, state)
            if proposal.action.upper() == "BACKCHANNEL":
                self.last_backchannel_at_ms = now_ms
            return self._decision(
                decision="play",
                reason=reason,
                proposal=proposal,
                priority=priority,
            )

        if proposal.action.upper() == "SPEAK" and reason in {
            "user_speaking_queue_dialogue",
            "speech_lane_busy",
        }:
            self.queue.append(proposal)
            return self._decision(
                decision="queue",
                reason=reason,
                proposal=proposal,
                priority=priority,
            )

        return self._decision(
            decision="reject",
            reason=reason,
            proposal=proposal,
            priority=priority,
        )

    def apply_control(
        self,
        action: ControlAction,
        state: SessionState,
        now_ms: int,
    ) -> dict[str, Any]:
        priority = _control_priority(action)
        action_name = action.action.upper()

        if action_name == "STOP_SPEAKING":
            stopped = self.current
            self.current = None
            self._clear_state(state)
            return {
                "decision": "stop",
                "lane": "speech",
                "reason": action.reason or "stop_speaking",
                "action_id": action.action_id,
                "priority": priority,
                "duck": False,
                "stopped": _proposal_payload(stopped),
                "now_ms": now_ms,
            }

        if action_name == "CANCEL_OUTPUT":
            stopped_current = self.current
            queue_before = len(self.queue)
            if action.target is None:
                self.current = None
                self.queue.clear()
            else:
                if self.current and self.current.proposal_id == action.target:
                    self.current = None
                self.queue = [
                    proposal
                    for proposal in self.queue
                    if proposal.proposal_id != action.target
                ]
            stopped = stopped_current if stopped_current is not self.current else None
            if stopped is not None:
                self._clear_state(state)
            cancelled_count = queue_before - len(self.queue)
            decision = "stop" if stopped is not None or cancelled_count else "no_op"
            return {
                "decision": decision,
                "lane": "speech",
                "reason": action.reason or "cancel_output",
                "action_id": action.action_id,
                "priority": priority,
                "duck": False,
                "stopped": _proposal_payload(stopped),
                "cancelled_queued": cancelled_count,
                "now_ms": now_ms,
            }

        return {
            "decision": "no_op",
            "lane": "speech",
            "reason": "unsupported_control_action",
            "action_id": action.action_id,
            "priority": priority,
            "duck": False,
            "now_ms": now_ms,
        }

    def finish_current(self, now_ms: int) -> dict[str, Any]:
        finished = self.current
        self.current = None
        return {
            "decision": "stop",
            "lane": "speech",
            "reason": "speech_finished",
            "proposal_id": finished.proposal_id if finished else None,
            "priority": _proposal_priority(finished) if finished else None,
            "duck": False,
            "finished": _proposal_payload(finished),
            "now_ms": now_ms,
        }

    def _is_interrupt(self, proposal: OutputProposal) -> bool:
        priority = _proposal_priority(proposal)
        return (
            priority >= self.priority_policy.INTERRUPT
            or proposal.interrupt_policy.get("can_preempt") is True
            or proposal.metadata.get("kind") == "interrupt"
        )

    def _is_dialogue(self, proposal: OutputProposal) -> bool:
        return proposal.agent.lower() == "dialogue"

    def _speech_busy(self, state: SessionState) -> bool:
        return (
            self.current is not None
            or state.assistant.is_speaking
            or state.assistant.speech_lane_busy
            or state.audio_runtime.speech_lane_busy
        )

    def _backchannel_in_cooldown(self, now_ms: int) -> bool:
        if self.last_backchannel_at_ms is None:
            return False
        return now_ms - self.last_backchannel_at_ms < self.cooldown_ms

    def _play(self, proposal: OutputProposal, state: SessionState) -> None:
        self.current = proposal
        state.assistant.is_speaking = True
        state.assistant.speech_lane_busy = True
        state.assistant.current_output = proposal.model_dump(mode="python")
        state.audio_runtime.speech_lane_busy = True

    def _clear_state(self, state: SessionState) -> None:
        state.assistant.is_speaking = False
        state.assistant.speech_lane_busy = False
        state.assistant.current_output = None
        state.audio_runtime.speech_lane_busy = False

    def _decision(
        self,
        decision: str,
        reason: str,
        proposal: OutputProposal,
        priority: int,
        preempted: OutputProposal | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "decision": decision,
            "lane": "speech",
            "reason": reason,
            "proposal_id": proposal.proposal_id,
            "priority": priority,
            "duck": False,
        }
        if preempted is not None:
            result["preempted"] = preempted.model_dump(mode="python")
        return result
