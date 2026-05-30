from __future__ import annotations

from time import time
from typing import Any

from realtime import EventBus, SessionStateManager
from schemas import ControlAction, Event, OutputProposal, SessionState
from schemas.event_types import CONTROL_ACTION, OUTPUT_PROPOSAL

from .ambience_lane import AmbienceLane
from .priority_policy import PriorityPolicy, effective_control_priority
from .sfx_lane import SFXLane
from .speech_lane import SpeechLane


def _now_ms() -> int:
    return int(time() * 1000)


class AudioOrchestrator:
    def __init__(
        self,
        session_state_manager: SessionStateManager | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.session_state_manager = session_state_manager or SessionStateManager()
        self.event_bus = event_bus
        self.speech_lane = SpeechLane()
        self.sfx_lane = SFXLane()
        self.ambience_lane = AmbienceLane()
        self.priority_policy = PriorityPolicy()

    def handle_output_proposal(
        self,
        proposal: OutputProposal,
        state: SessionState | None = None,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        current_state = state or self.session_state_manager.get_or_create(
            proposal.session_id
        )
        timestamp_ms = now_ms if now_ms is not None else _now_ms()
        lane = proposal.lane.lower()

        if lane == "speech":
            return self.speech_lane.apply_proposal(
                proposal=proposal,
                state=current_state,
                now_ms=timestamp_ms,
            )
        if lane == "sfx":
            return self.sfx_lane.apply_proposal(
                proposal=proposal,
                state=current_state,
                now_ms=timestamp_ms,
            )
        if lane == "ambience":
            return self.ambience_lane.apply_proposal(
                proposal=proposal,
                state=current_state,
                now_ms=timestamp_ms,
            )

        return {
            "decision": "reject",
            "lane": lane,
            "reason": "unsupported_lane",
            "proposal_id": proposal.proposal_id,
            "priority": proposal.priority,
            "duck": False,
            "now_ms": timestamp_ms,
        }

    def handle_control_action(
        self,
        action: ControlAction,
        state: SessionState | None = None,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        current_state = state or self.session_state_manager.get_or_create(
            action.session_id
        )
        timestamp_ms = now_ms if now_ms is not None else _now_ms()
        action_name = action.action.upper()
        priority = effective_control_priority(
            action=action.action,
            agent=action.agent,
            priority=action.priority,
            explicit_fields=action.model_fields_set,
        )

        if action_name == "STOP_SPEAKING":
            decision = self.speech_lane.apply_control(
                action=action,
                state=current_state,
                now_ms=timestamp_ms,
            )
            reason = action.reason or "speech_stopped"
            decision["side_effects"] = [
                self.sfx_lane.duck_all(reason=reason),
                self.ambience_lane.duck(reason=reason),
            ]
            return decision

        if action_name == "INTERRUPT_USER":
            interrupt_proposal = action.payload.get("interrupt_proposal")
            if interrupt_proposal is not None:
                proposal = self._coerce_proposal(
                    interrupt_proposal,
                    session_id=action.session_id,
                )
                decision = self.handle_output_proposal(
                    proposal=proposal,
                    state=current_state,
                    now_ms=timestamp_ms,
                )
                decision["action_id"] = action.action_id
                return decision
            return {
                "decision": "no_op",
                "lane": "speech",
                "reason": "interrupt_user_requires_proposal",
                "action_id": action.action_id,
                "priority": priority,
                "duck": False,
                "now_ms": timestamp_ms,
            }

        if action_name == "DUCK_AUDIO":
            reason = action.reason or "duck_audio"
            return {
                "decision": "duck",
                "lane": "sfx",
                "reason": reason,
                "action_id": action.action_id,
                "priority": priority,
                "duck": True,
                "now_ms": timestamp_ms,
                "side_effects": [
                    self.sfx_lane.duck_all(reason=reason),
                    self.ambience_lane.duck(reason=reason),
                ],
            }

        if action_name == "CANCEL_OUTPUT":
            return self.speech_lane.apply_control(
                action=action,
                state=current_state,
                now_ms=timestamp_ms,
            )

        return {
            "decision": "no_op",
            "lane": "speech",
            "reason": "unsupported_control_action",
            "action_id": action.action_id,
            "priority": priority,
            "duck": False,
            "now_ms": timestamp_ms,
        }

    def handle_event(self, event: Event) -> list[dict[str, Any]]:
        if event.type == OUTPUT_PROPOSAL:
            proposal = self._coerce_proposal(event.payload, session_id=event.session_id)
            return [self.handle_output_proposal(proposal)]

        if event.type == CONTROL_ACTION:
            action = self._coerce_control_action(
                event.payload,
                session_id=event.session_id,
            )
            return [self.handle_control_action(action)]

        return [
            {
                "decision": "no_op",
                "lane": "speech",
                "reason": "unsupported_event_type",
                "event_id": event.event_id,
                "priority": None,
                "duck": False,
            }
        ]

    def get_state_snapshot(self) -> dict[str, Any]:
        speech_current = self.speech_lane.current
        ambience_current = self.ambience_lane.current
        return {
            "speech": {
                "current": (
                    speech_current.model_dump(mode="python")
                    if speech_current is not None
                    else None
                ),
                "queue_length": len(self.speech_lane.queue),
            },
            "sfx": {
                "active_count": len(self.sfx_lane.active),
                "active": [
                    proposal.model_dump(mode="python")
                    for proposal in self.sfx_lane.active
                ],
            },
            "ambience": {
                "current": (
                    ambience_current.model_dump(mode="python")
                    if ambience_current is not None
                    else None
                ),
            },
        }

    def _coerce_proposal(
        self,
        payload: OutputProposal | dict[str, Any],
        session_id: str,
    ) -> OutputProposal:
        if isinstance(payload, OutputProposal):
            return payload
        proposal_payload = payload.get("proposal", payload)
        if not isinstance(proposal_payload, dict):
            raise TypeError("OUTPUT_PROPOSAL payload must be a dict")
        proposal_payload = dict(proposal_payload)
        proposal_payload.setdefault("session_id", session_id)
        return OutputProposal.model_validate(proposal_payload)

    def _coerce_control_action(
        self,
        payload: ControlAction | dict[str, Any],
        session_id: str,
    ) -> ControlAction:
        if isinstance(payload, ControlAction):
            return payload
        control_payload = payload.get("control_action", payload)
        if not isinstance(control_payload, dict):
            raise TypeError("CONTROL_ACTION payload must be a dict")
        control_payload = dict(control_payload)
        control_payload.setdefault("session_id", session_id)
        return ControlAction.model_validate(control_payload)
