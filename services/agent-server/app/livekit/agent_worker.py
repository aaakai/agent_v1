from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from asr import (
    ASRDiagnosticsStore,
    ASRProviderConfig,
    ASRTrigger,
    create_asr_adapter,
)
from audio_input import AudioFeatureExtractor, BackchannelTrigger, RawAudioRouter
from runtime import RuntimeCoordinator

from .audio_track_reader import LiveKitAudioTrackReader
from .config import LiveKitConfig
from .debug_state import LiveKitDebugState
from .room_connection import (
    connect_room,
    create_livekit_room,
    disconnect_room,
    register_room_event,
)
from .room_handler import LiveKitRoomHandler
from .token import LiveKitTokenRequest, create_token


class LiveKitAgentWorkerOptions(BaseModel):
    room_name: str | None = None
    agent_identity: str | None = None
    connect_timeout_seconds: float = 15.0
    run_duration_seconds: float | None = None
    auto_subscribe: bool = True
    sample_rate: int = 16000
    channels: int = 1
    enable_runtime_consumers: bool = True
    asr_provider: str | None = None
    asr_language: str | None = None
    asr_model: str | None = None
    asr_enabled: bool = True
    asr_chunk_duration_ms: int | None = None
    asr_min_chunk_duration_ms: int | None = None
    asr_max_buffer_duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveKitAgentWorkerResult(BaseModel):
    connected: bool
    room_name: str | None
    agent_identity: str | None
    frames_received: int = 0
    tracks_subscribed: int = 0
    participants_seen: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    debug_state: dict[str, Any] = Field(default_factory=dict)


class LiveKitAgentWorker:
    def __init__(
        self,
        config: LiveKitConfig,
        options: LiveKitAgentWorkerOptions | None = None,
        raw_audio_router: RawAudioRouter | None = None,
        runtime_coordinator: RuntimeCoordinator | None = None,
        debug_state: LiveKitDebugState | None = None,
        room_handler: LiveKitRoomHandler | None = None,
    ) -> None:
        self.config = config
        self.options = options or LiveKitAgentWorkerOptions()
        self.raw_audio_router = raw_audio_router or RawAudioRouter()
        self.runtime_coordinator = runtime_coordinator or RuntimeCoordinator()
        self.debug_state = debug_state or LiveKitDebugState()
        self.room_handler = room_handler or LiveKitRoomHandler(
            config=config,
            raw_audio_router=self.raw_audio_router,
            runtime_coordinator=self.runtime_coordinator,
            debug_state=self.debug_state,
        )
        self.room: Any | None = None
        self.tracks_subscribed = 0
        self.participants_seen = 0
        self.errors: list[dict[str, Any]] = []
        self.audio_track_reader_cls = LiveKitAudioTrackReader
        self.asr_config = self._build_asr_config()
        self.asr_adapter = create_asr_adapter(self.asr_config)
        self.asr_diagnostics = ASRDiagnosticsStore()
        self.asr_trigger: ASRTrigger | None = None
        self._refresh_asr_status()

        if self.options.enable_runtime_consumers:
            self._ensure_runtime_consumers()

    def create_agent_token(self) -> str:
        room_name = self._room_name()
        identity = self._agent_identity()
        request = LiveKitTokenRequest(
            room_name=room_name,
            identity=identity,
            name=identity,
            can_publish=True,
            can_subscribe=True,
        )
        return create_token(self.config, request, allow_mock=False).token

    async def connect_and_run(self) -> LiveKitAgentWorkerResult:
        if not self.config.is_configured():
            raise ValueError("LiveKit config is incomplete")

        room_name = self._room_name()
        identity = self._agent_identity()
        token = self.create_agent_token()
        self.room = create_livekit_room()
        self._register_room_callbacks(self.room)

        try:
            await asyncio.wait_for(
                connect_room(self.room, self.config.url or "", token),
                timeout=self.options.connect_timeout_seconds,
            )
            self.debug_state.mark_connected(room_name=room_name, agent_identity=identity)

            if self.options.run_duration_seconds is not None:
                await asyncio.sleep(self.options.run_duration_seconds)
                await self.disconnect()
            else:
                while True:
                    await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await self.disconnect()
            raise
        except Exception as exc:
            error = {"error": str(exc)}
            self.errors.append(error)
            self.debug_state.append_event(
                "worker_error",
                str(exc),
                room_name=room_name,
                metadata={"error": str(exc)},
            )
            raise

        return self._result()

    async def disconnect(self) -> None:
        if self.room is not None:
            await disconnect_room(self.room)
        self.debug_state.mark_disconnected(reason="worker_disconnect")
        await self.room_handler.stop_all_reader_tasks()

    def _register_room_callbacks(self, room: Any) -> None:
        def participant_connected(participant: Any) -> None:
            identity = self._participant_identity(participant)
            self.participants_seen += 1
            self.debug_state.mark_participant_joined(
                identity,
                metadata={"sid": getattr(participant, "sid", None)},
            )

        def participant_disconnected(participant: Any) -> None:
            identity = self._participant_identity(participant)
            self.debug_state.append_event(
                "participant_disconnected",
                f"Participant disconnected: {identity}",
                participant_identity=identity,
            )

        def track_subscribed(*args: Any) -> None:
            track, publication, participant = self._normalize_track_args(args)
            self._schedule(self._handle_track_subscribed(track, publication, participant))

        def track_unsubscribed(*args: Any) -> None:
            track, publication, participant = self._normalize_track_args(args)
            self.debug_state.append_event(
                "track_unsubscribed",
                "Track unsubscribed",
                participant_identity=self._participant_identity(participant),
                track_sid=self._track_sid(publication, track),
            )

        def disconnected(reason: Any = None) -> None:
            self.debug_state.mark_disconnected(reason=str(reason) if reason else None)

        register_room_event(room, "participant_connected", participant_connected)
        register_room_event(room, "participant_disconnected", participant_disconnected)
        register_room_event(room, "track_subscribed", track_subscribed)
        register_room_event(room, "track_unsubscribed", track_unsubscribed)
        register_room_event(room, "disconnected", disconnected)

    async def _handle_track_subscribed(
        self,
        track: Any,
        publication: Any | None,
        participant: Any | None,
    ) -> None:
        participant_identity = self._participant_identity(participant)
        track_sid = self._track_sid(publication, track)

        if not self._is_audio_track(track, publication):
            self.debug_state.append_event(
                "track_ignored",
                "Ignored non-audio track",
                participant_identity=participant_identity,
                track_sid=track_sid,
                metadata={"kind": str(getattr(track, "kind", getattr(publication, "kind", "")))},
            )
            return

        self.tracks_subscribed += 1
        self.debug_state.mark_track_subscribed(
            track_sid=track_sid,
            participant_identity=participant_identity,
            metadata={"source": getattr(publication, "source", None)},
        )

        reader = self.audio_track_reader_cls(
            track=track,
            session_id=participant_identity,
            sample_rate=self.options.sample_rate,
            channels=self.options.channels,
        )
        result = await self.room_handler.handle_audio_reader(reader)
        self.errors.extend(result.get("errors", []))

    def _is_audio_track(self, track: Any, publication: Any | None = None) -> bool:
        for candidate in (getattr(track, "kind", None), getattr(publication, "kind", None)):
            if candidate is None:
                continue
            value = str(candidate).lower()
            if "audio" in value:
                return True
            if "video" in value:
                return False

        source = getattr(publication, "source", None)
        if source is not None and str(source).lower() == "microphone":
            return True
        return True

    def _participant_identity(self, participant: Any | None) -> str:
        if participant is None:
            return "unknown-participant"
        identity = getattr(participant, "identity", None)
        if identity:
            return str(identity)
        sid = getattr(participant, "sid", None)
        if sid:
            return str(sid)
        return "unknown-participant"

    def _track_sid(self, publication: Any | None, track: Any | None) -> str:
        if publication is not None:
            sid = getattr(publication, "sid", None)
            if sid:
                return str(sid)
        if track is not None:
            sid = getattr(track, "sid", None)
            if sid:
                return str(sid)
        return "unknown-track"

    def _room_name(self) -> str:
        return self.options.room_name or self.config.default_room_name()

    def _agent_identity(self) -> str:
        return self.options.agent_identity or self.config.agent_identity or "lulula-agent"

    def _ensure_runtime_consumers(self) -> None:
        room_name = self._room_name()
        names = set(self.raw_audio_router.get_consumer_names())
        if "backchannel" not in names:
            self.raw_audio_router.add_consumer(
                "backchannel",
                BackchannelTrigger(
                    session_id=room_name,
                    runtime_coordinator=self.runtime_coordinator,
                    extractor=AudioFeatureExtractor(),
                ).consume,
            )
        if "asr" not in names:
            self.asr_trigger = ASRTrigger(
                session_id=room_name,
                runtime_coordinator=self.runtime_coordinator,
                asr_adapter=self.asr_adapter,
                diagnostics=self.asr_diagnostics,
            )
            self.raw_audio_router.add_consumer(
                "asr",
                self._consume_asr,
            )

    def _normalize_track_args(self, args: tuple[Any, ...]) -> tuple[Any, Any | None, Any | None]:
        track = args[0] if len(args) >= 1 else None
        publication = args[1] if len(args) >= 2 else None
        participant = args[2] if len(args) >= 3 else None
        return track, publication, participant

    def _schedule(self, coroutine: Any) -> None:
        try:
            asyncio.get_running_loop().create_task(coroutine)
        except RuntimeError:
            asyncio.run(coroutine)

    async def _consume_asr(self, frame: Any) -> list[dict[str, Any]]:
        if self.asr_trigger is None:
            return []
        decisions = await self.asr_trigger.consume(frame)
        self._refresh_asr_status()
        for decision in decisions:
            if decision.get("type") == "asr_error":
                self.debug_state.record_asr_error(
                    str(decision.get("error", "")),
                    metadata={"provider": decision.get("provider")},
                )
        return decisions

    def _build_asr_config(self) -> ASRProviderConfig:
        config = ASRProviderConfig.from_env()
        updates: dict[str, Any] = {
            "sample_rate": self.options.sample_rate,
            "channels": self.options.channels,
        }
        if not self.options.asr_enabled:
            updates["provider"] = "disabled"
        elif self.options.asr_provider:
            updates["provider"] = self.options.asr_provider
        if self.options.asr_language:
            updates["language"] = self.options.asr_language
        if self.options.asr_model:
            updates["model"] = self.options.asr_model
        if self.options.asr_chunk_duration_ms is not None:
            updates["chunk_duration_ms"] = self.options.asr_chunk_duration_ms
        if self.options.asr_min_chunk_duration_ms is not None:
            updates["min_chunk_duration_ms"] = self.options.asr_min_chunk_duration_ms
        if self.options.asr_max_buffer_duration_ms is not None:
            updates["max_buffer_duration_ms"] = self.options.asr_max_buffer_duration_ms
        return config.model_copy(update=updates).with_env_credentials()

    def _refresh_asr_status(self) -> None:
        status = self.asr_adapter.get_status().model_dump(mode="python")
        status["config"] = self.asr_config.to_safe_dict()
        if self.asr_trigger is not None:
            status["trigger"] = self.asr_trigger.get_status()
        self.debug_state.update_asr_status(status)

    def _result(self) -> LiveKitAgentWorkerResult:
        snapshot = self.debug_state.snapshot()
        return LiveKitAgentWorkerResult(
            connected=bool(snapshot.get("connected")),
            room_name=self._room_name(),
            agent_identity=self._agent_identity(),
            frames_received=int(snapshot.get("frames_received", 0)),
            tracks_subscribed=self.tracks_subscribed,
            participants_seen=self.participants_seen,
            errors=list(self.errors),
            debug_state=snapshot,
        )
