from __future__ import annotations

import asyncio
import struct
from typing import Any

from pydantic import BaseModel, Field

from asr import ASRTrigger, MockASRAdapter
from audio_runtime import AmbienceController
from audio_input import (
    AudioFeatureExtractor,
    AudioFrame,
    BackchannelTrigger,
    EnergyVAD,
    RawAudioRouter,
)
from schemas import Event
from schemas.event_types import (
    ASSISTANT_SPEECH_START,
    AUDIO_FEATURE_UPDATE,
    SCENE_CHANGED,
    USER_SPEECH_END,
)

from .coordinator import RuntimeCoordinator


class DebugFrameSpec(BaseModel):
    timestamp_ms: int | None = None
    pcm_kind: str = "silence"
    duration_ms: int = 100
    sample_rate: int = 16000
    channels: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class DebugScenario(BaseModel):
    name: str
    session_id: str
    description: str
    frames: list[DebugFrameSpec]
    pre_events: list[Event] = Field(default_factory=list)
    post_events: list[Event] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DebugSessionResult(BaseModel):
    scenario: str
    session_id: str
    frames_processed: int
    event_count: int
    decision_count: int
    decisions: list[dict[str, Any]]
    final_state: dict[str, Any]
    errors: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)


def make_pcm(kind: str, duration_ms: int, sample_rate: int = 16000) -> bytes:
    sample_count = int(sample_rate * duration_ms / 1000)
    if sample_count <= 0:
        return b""

    if kind == "silence":
        return b"\x00\x00" * sample_count
    if kind == "speech":
        amplitude = 6000
    elif kind == "loud_speech":
        amplitude = 18000
    else:
        raise ValueError(f"unknown pcm kind: {kind}")

    return b"".join(
        struct.pack("<h", amplitude if index % 2 == 0 else -amplitude)
        for index in range(sample_count)
    )


def make_audio_frame(
    session_id: str,
    spec: DebugFrameSpec,
    base_timestamp_ms: int,
) -> AudioFrame:
    samples_per_channel = int(spec.sample_rate * spec.duration_ms / 1000)
    return AudioFrame(
        session_id=session_id,
        timestamp_ms=spec.timestamp_ms or base_timestamp_ms,
        sample_rate=spec.sample_rate,
        channels=spec.channels,
        samples_per_channel=samples_per_channel,
        pcm=make_pcm(spec.pcm_kind, spec.duration_ms, spec.sample_rate),
        source="debug_runner",
        metadata=dict(spec.metadata),
    )


def flatten_decisions_from_route_summary(
    route_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for value in route_summary.get("consumer_results", {}).values():
        if isinstance(value, list):
            decisions.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            decisions.append(value)
    return decisions


def result_to_json_dict(result: DebugSessionResult) -> dict[str, Any]:
    return result.model_dump(mode="python")


class DebugSessionRunner:
    DEFAULT_SESSION_ID = "debug_session"
    SCENARIOS = {
        "ambience",
        "backchannel",
        "bargein",
        "danger",
        "factual",
        "full",
        "normal",
        "scene",
        "sfx",
    }

    def __init__(
        self,
        runtime_coordinator: RuntimeCoordinator | None = None,
        raw_audio_router: RawAudioRouter | None = None,
        backchannel_trigger: BackchannelTrigger | None = None,
        asr_trigger: ASRTrigger | None = None,
        asr_adapter: MockASRAdapter | None = None,
    ) -> None:
        self.runtime_coordinator = runtime_coordinator or RuntimeCoordinator()
        self.raw_audio_router = raw_audio_router or RawAudioRouter()
        self.asr_adapter = asr_adapter or MockASRAdapter()
        self.backchannel_trigger = backchannel_trigger or BackchannelTrigger(
            session_id=self.DEFAULT_SESSION_ID,
            runtime_coordinator=self.runtime_coordinator,
            extractor=AudioFeatureExtractor(
                vad=EnergyVAD(energy_threshold=0.01, min_speech_frames=2)
            ),
        )
        self.asr_trigger = asr_trigger or ASRTrigger(
            session_id=self.DEFAULT_SESSION_ID,
            runtime_coordinator=self.runtime_coordinator,
            asr_adapter=self.asr_adapter,
        )
        self._ensure_default_consumers()

    async def run_scenario(self, scenario: DebugScenario) -> DebugSessionResult:
        decisions: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        route_summaries: list[dict[str, Any]] = []

        for event in scenario.pre_events:
            decisions.extend(self.runtime_coordinator.process_event(event))

        if "ambience_scene" in scenario.metadata:
            controller = AmbienceController()
            proposal = controller.ambience_for_scene(
                session_id=scenario.session_id,
                scene_name=scenario.metadata["ambience_scene"],
            )
            state = self.runtime_coordinator.get_session_state(scenario.session_id)
            ambience_decision = self.runtime_coordinator.orchestrator.handle_output_proposal(
                proposal,
                state=state,
            )
            ambience_decision["proposal_action"] = proposal.action
            ambience_decision["agent"] = proposal.agent
            ambience_decision["session_id"] = scenario.session_id
            decisions.append(ambience_decision)

        frames_processed = 0
        next_timestamp_ms = 1000
        for spec in scenario.frames:
            frame = make_audio_frame(
                session_id=scenario.session_id,
                spec=spec,
                base_timestamp_ms=next_timestamp_ms,
            )
            route_summary = await self.raw_audio_router.route(frame)
            route_summaries.append(route_summary)
            decisions.extend(flatten_decisions_from_route_summary(route_summary))
            errors.extend(route_summary.get("errors", []))
            frames_processed += 1
            next_timestamp_ms = frame.timestamp_ms + spec.duration_ms

        for event in scenario.post_events:
            decisions.extend(self.runtime_coordinator.process_event(event))

        final_state = self.runtime_coordinator.get_session_state(scenario.session_id)
        return DebugSessionResult(
            scenario=scenario.name,
            session_id=scenario.session_id,
            frames_processed=frames_processed,
            event_count=len(final_state.events),
            decision_count=len(decisions),
            decisions=decisions,
            final_state=final_state.model_dump(mode="python"),
            errors=errors,
            metadata={
                "scenario": scenario.metadata,
                "consumer_names": self.raw_audio_router.get_consumer_names(),
                "route_summaries": route_summaries,
            },
        )

    def run_scenario_sync(self, scenario: DebugScenario) -> DebugSessionResult:
        return asyncio.run(self.run_scenario(scenario))

    def get_available_scenarios(self) -> list[str]:
        return sorted(self.SCENARIOS)

    def build_scenario(
        self,
        name: str,
        session_id: str | None = None,
    ) -> DebugScenario:
        active_session_id = session_id or f"debug_{name}"
        if name == "backchannel":
            return self._backchannel_scenario(active_session_id)
        if name == "danger":
            return self._danger_scenario(active_session_id)
        if name == "factual":
            return self._factual_scenario(active_session_id)
        if name == "bargein":
            return self._bargein_scenario(active_session_id)
        if name == "normal":
            return self._normal_scenario(active_session_id)
        if name == "full":
            return self._full_scenario(active_session_id)
        if name == "sfx":
            return self._sfx_scenario(active_session_id)
        if name == "scene":
            return self._scene_scenario(active_session_id)
        if name == "ambience":
            return self._ambience_scenario(active_session_id)
        raise ValueError(f"unknown debug scenario: {name}")

    def _ensure_default_consumers(self) -> None:
        names = set(self.raw_audio_router.get_consumer_names())
        if "backchannel" not in names:
            self.raw_audio_router.add_consumer(
                "backchannel",
                self.backchannel_trigger.consume,
            )
        if "asr" not in names:
            self.raw_audio_router.add_consumer("asr", self.asr_trigger.consume)

    def _backchannel_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="backchannel",
            session_id=session_id,
            description="User speech followed by a short pause that invites a backchannel.",
            frames=[
                DebugFrameSpec(timestamp_ms=1000, pcm_kind="speech"),
                DebugFrameSpec(timestamp_ms=1100, pcm_kind="speech"),
                DebugFrameSpec(timestamp_ms=1400, pcm_kind="silence"),
            ],
        )

    def _danger_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="danger",
            session_id=session_id,
            description="ASR partial contains a dangerous operation request.",
            frames=[
                DebugFrameSpec(
                    timestamp_ms=1000,
                    pcm_kind="speech",
                    metadata={"asr_text": "我准备直接删库", "asr_final": False},
                )
            ],
        )

    def _factual_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="factual",
            session_id=session_id,
            description="ASR partial contains an obvious factual error.",
            frames=[
                DebugFrameSpec(
                    timestamp_ms=1000,
                    pcm_kind="speech",
                    metadata={"asr_text": "一加一等于三", "asr_final": False},
                )
            ],
        )

    def _bargein_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="bargein",
            session_id=session_id,
            description="Assistant is speaking when the user loudly barges in.",
            pre_events=[
                Event(session_id=session_id, type=ASSISTANT_SPEECH_START),
            ],
            frames=[
                DebugFrameSpec(timestamp_ms=1000, pcm_kind="loud_speech"),
            ],
        )

    def _normal_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="normal",
            session_id=session_id,
            description="Normal ASR final followed by user turn end.",
            frames=[
                DebugFrameSpec(
                    timestamp_ms=1000,
                    pcm_kind="speech",
                    metadata={
                        "asr_text": "我想聊一下这个架构",
                        "asr_final": True,
                    },
                )
            ],
            post_events=[
                Event(session_id=session_id, type=USER_SPEECH_END),
            ],
        )

    def _full_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="full",
            session_id=session_id,
            description="Backchannel, ASR final, dialogue, assistant speech, and barge-in.",
            frames=[
                DebugFrameSpec(
                    timestamp_ms=1000,
                    pcm_kind="speech",
                    metadata={
                        "asr_text": "我想聊一下这个架构",
                        "asr_final": False,
                    },
                ),
                DebugFrameSpec(timestamp_ms=1100, pcm_kind="speech"),
                DebugFrameSpec(timestamp_ms=1400, pcm_kind="silence"),
                DebugFrameSpec(
                    timestamp_ms=1700,
                    pcm_kind="speech",
                    metadata={
                        "asr_text": "我想聊一下这个架构",
                        "asr_final": True,
                    },
                ),
            ],
            post_events=[
                Event(session_id=session_id, type=USER_SPEECH_END),
                Event(session_id=session_id, type=ASSISTANT_SPEECH_START),
                Event(
                    session_id=session_id,
                    type=AUDIO_FEATURE_UPDATE,
                    payload={"is_speaking": True, "barge_in_score": 0.9},
                ),
            ],
        )

    def _sfx_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="sfx",
            session_id=session_id,
            description="ASR final mentions a door knock and triggers a spatial SFX proposal.",
            frames=[
                DebugFrameSpec(
                    timestamp_ms=1000,
                    pcm_kind="speech",
                    metadata={
                        "asr_text": "突然有人敲门",
                        "asr_final": True,
                    },
                )
            ],
            post_events=[
                Event(session_id=session_id, type=USER_SPEECH_END),
            ],
        )

    def _scene_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="scene",
            session_id=session_id,
            description="Scene changes to rainy_alley and updates scene state.",
            frames=[],
            pre_events=[
                Event(
                    session_id=session_id,
                    type=SCENE_CHANGED,
                    payload={
                        "name": "rainy_alley",
                        "mood": "tense",
                        "ambience": "rain_alley_loop",
                        "metadata": {"reverb": "wet_alley"},
                    },
                )
            ],
        )

    def _ambience_scenario(self, session_id: str) -> DebugScenario:
        return DebugScenario(
            name="ambience",
            session_id=session_id,
            description="Ambience controller creates a SET_AMBIENCE proposal.",
            frames=[],
            metadata={"ambience_scene": "rainy_alley"},
        )
