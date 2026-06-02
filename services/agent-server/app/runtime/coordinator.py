from __future__ import annotations

import asyncio
from typing import Any

from agents import (
    AgentResult,
    BaseAgent,
    MockBackchannelAgent,
    MockDialogueAgent,
    MockInterruptAgent,
    MockSceneAgent,
    MockSFXPlannerAgent,
    MockSpatialAudioAgent,
    SafetyPolicyAgent,
)
from orchestrator import AudioOrchestrator
from realtime import EventBus, SessionStateManager
from schemas import ControlAction, Event, OutputProposal, SessionState, StateUpdate
from schemas.event_types import (
    ASR_FINAL,
    ASR_PARTIAL,
    ASSISTANT_SPEECH_END,
    ASSISTANT_SPEECH_START,
    AUDIO_FEATURE_UPDATE,
    SCENE_CHANGED,
    USER_AUDIO_FRAME,
    USER_SPEECH_END,
    USER_SPEECH_PAUSE,
    USER_SPEECH_START,
)


class RuntimeCoordinator:
    def __init__(
        self,
        session_state_manager: SessionStateManager | None = None,
        event_bus: EventBus | None = None,
        agents: list[BaseAgent] | None = None,
        orchestrator: AudioOrchestrator | None = None,
    ) -> None:
        self.session_state_manager = session_state_manager or SessionStateManager()
        self.event_bus = event_bus or EventBus()
        self.agents = agents if agents is not None else self._default_agents()
        self.orchestrator = orchestrator or AudioOrchestrator(
            session_state_manager=self.session_state_manager,
            event_bus=self.event_bus,
        )

    def process_event(self, event: Event | dict[str, Any]) -> list[dict[str, Any]]:
        normalized = event if isinstance(event, Event) else Event.model_validate(event)
        state = self._apply_event_to_state(normalized)
        self.session_state_manager.append_event(normalized.session_id, normalized)
        self._publish_event(normalized)

        agent_results = self._run_agents(normalized, state)
        state_updates = [
            update for result in agent_results for update in result.state_updates
        ]
        proposals = [proposal for result in agent_results for proposal in result.proposals]
        control_actions = [
            action for result in agent_results for action in result.control_actions
        ]

        state = self._apply_state_updates(normalized.session_id, state_updates)
        decisions: list[dict[str, Any]] = []

        for proposal in proposals:
            proposal = self._enhance_proposal(proposal, state)
            allowed, reason = self._validate_proposal(proposal, state)
            if not allowed:
                decision = self._proposal_reject_decision(proposal, reason)
            else:
                decision = self.orchestrator.handle_output_proposal(
                    proposal,
                    state=state,
                    now_ms=normalized.timestamp_ms,
                )
                decision["proposal_action"] = proposal.action
                decision["agent"] = proposal.agent
            decision.setdefault("proposal", proposal.model_dump(mode="python"))
            self._annotate_decision(decision, normalized)
            decisions.append(decision)

        for action in control_actions:
            state = self._apply_control_metadata(action, state)
            decision = self.orchestrator.handle_control_action(
                action,
                state=state,
                now_ms=normalized.timestamp_ms,
            )
            decision["control_action"] = action.action
            decision["control_reason"] = action.reason
            decision["agent"] = action.agent
            self._annotate_decision(decision, normalized)
            decisions.append(decision)

        return decisions

    def process_events(self, events: list[Event | dict[str, Any]]) -> list[dict[str, Any]]:
        decisions: list[dict[str, Any]] = []
        for event in events:
            decisions.extend(self.process_event(event))
        return decisions

    def get_session_state(self, session_id: str) -> SessionState:
        return self.session_state_manager.get_or_create(session_id)

    def _apply_event_to_state(self, event: Event) -> SessionState:
        payload = event.payload
        patch: dict[str, Any] = {}

        if event.type == USER_SPEECH_START:
            patch = {"user_audio": {"is_speaking": True}}
        elif event.type == USER_SPEECH_PAUSE:
            patch = {"user_audio": {"pause_ms": payload.get("pause_ms", 0)}}
        elif event.type == USER_SPEECH_END:
            patch = {"user_audio": {"is_speaking": False}}
        elif event.type == ASR_PARTIAL:
            patch = {
                "asr": {
                    "partial": payload.get("text"),
                    "stability": payload.get("stability", 0.0),
                    "updated_at_ms": event.timestamp_ms,
                }
            }
        elif event.type == ASR_FINAL:
            patch = {
                "asr": {
                    "final": payload.get("text"),
                    "partial": None,
                    "stability": 1.0,
                    "updated_at_ms": event.timestamp_ms,
                }
            }
        elif event.type == ASSISTANT_SPEECH_START:
            patch = {
                "assistant": {"is_speaking": True, "speech_lane_busy": True},
                "audio_runtime": {"speech_lane_busy": True},
            }
        elif event.type == ASSISTANT_SPEECH_END:
            patch = {
                "assistant": {
                    "is_speaking": False,
                    "speech_lane_busy": False,
                    "current_output": None,
                },
                "audio_runtime": {"speech_lane_busy": False},
            }
        elif event.type == SCENE_CHANGED:
            scene_patch = {
                key: payload[key]
                for key in ("name", "mood", "ambience", "metadata")
                if key in payload
            }
            patch = {"scene": scene_patch}
        elif event.type in {AUDIO_FEATURE_UPDATE, USER_AUDIO_FRAME}:
            user_audio_patch = {
                key: payload[key]
                for key in (
                    "energy",
                    "pause_ms",
                    "emotion",
                    "backchannel_opportunity",
                    "barge_in_score",
                    "is_speaking",
                )
                if key in payload
            }
            patch = {"user_audio": user_audio_patch}

        if not patch:
            return self.session_state_manager.get_or_create(event.session_id)
        return self.session_state_manager.update(event.session_id, patch)

    def _apply_control_metadata(
        self,
        action: ControlAction,
        state: SessionState,
    ) -> SessionState:
        if (
            action.action.upper() == "INTERRUPT_USER"
            and action.payload.get("followup_needed") is True
        ):
            return self.session_state_manager.update(
                state.session_id,
                {
                    "metadata": {
                        "interrupt_reason": action.reason,
                        "interrupt_phrase": action.payload.get("interrupt_phrase"),
                        "followup_needed": True,
                        "followup_emitted": False,
                    }
                },
            )
        return state

    def _run_agents(self, event: Event, state: SessionState) -> list[AgentResult]:
        results: list[AgentResult] = []
        for agent in self.agents:
            results.append(agent.observe(event, state))
        for agent in self.agents:
            results.append(agent.propose(state))
        return results

    def _apply_state_updates(
        self,
        session_id: str,
        state_updates: list[StateUpdate],
    ) -> SessionState:
        state = self.session_state_manager.get_or_create(session_id)
        for update in state_updates:
            state = self.session_state_manager.update(session_id, update.patch)
        return state

    def _enhance_proposal(
        self,
        proposal: OutputProposal,
        state: SessionState,
    ) -> OutputProposal:
        enhanced = proposal
        for agent in self.agents:
            enhancer = getattr(agent, "enhance_sfx_proposal", None)
            if callable(enhancer):
                enhanced = enhancer(enhanced, state)
        return enhanced

    def _validate_proposal(
        self,
        proposal: OutputProposal,
        state: SessionState,
    ) -> tuple[bool, str]:
        for agent in self.agents:
            validator = getattr(agent, "validate_proposal", None)
            if callable(validator):
                allowed, reason = validator(proposal, state)
                if not allowed:
                    return False, reason
        return True, "allowed"

    def _publish_event(self, event: Event) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.event_bus.publish(event))
            return
        loop.create_task(self.event_bus.publish(event))

    def _annotate_decision(self, decision: dict[str, Any], event: Event) -> None:
        decision.setdefault("event_id", event.event_id)
        decision.setdefault("event_type", event.type)
        decision.setdefault("event_timestamp_ms", event.timestamp_ms)
        decision.setdefault("session_id", event.session_id)

    def _proposal_reject_decision(
        self,
        proposal: OutputProposal,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "decision": "reject",
            "lane": proposal.lane,
            "reason": reason,
            "proposal_id": proposal.proposal_id,
            "proposal_action": proposal.action,
            "priority": proposal.priority,
            "duck": False,
            "agent": proposal.agent,
        }

    def _default_agents(self) -> list[BaseAgent]:
        return [
            MockBackchannelAgent(),
            MockInterruptAgent(),
            MockDialogueAgent(),
            MockSceneAgent(),
            MockSFXPlannerAgent(),
            MockSpatialAudioAgent(),
            SafetyPolicyAgent(),
        ]
