from __future__ import annotations

from typing import Any

from schemas import Event
from schemas.event_types import AUDIO_FEATURE_UPDATE

from .audio_frame import AudioFrame
from .vad import EnergyVAD


class AudioFeatureExtractor:
    def __init__(
        self,
        vad: EnergyVAD | None = None,
        pause_threshold_ms: int = 200,
        backchannel_pause_min_ms: int = 200,
        backchannel_pause_max_ms: int = 500,
    ) -> None:
        self.vad = vad or EnergyVAD()
        self.pause_threshold_ms = pause_threshold_ms
        self.backchannel_pause_min_ms = backchannel_pause_min_ms
        self.backchannel_pause_max_ms = backchannel_pause_max_ms
        self.last_speech_timestamp_ms: int | None = None
        self.current_pause_ms = 0
        self.last_state = "silence"

    def extract(self, frame: AudioFrame) -> dict[str, Any]:
        vad_result = self.vad.update(frame)
        frame_is_speech = vad_result["is_speech"]
        is_speaking = vad_result["state"] == "speech" or frame_is_speech

        if frame_is_speech:
            self.last_speech_timestamp_ms = frame.timestamp_ms
            self.current_pause_ms = 0
        elif self.last_speech_timestamp_ms is not None:
            self.current_pause_ms = max(
                0,
                frame.timestamp_ms - self.last_speech_timestamp_ms,
            )
        else:
            self.current_pause_ms = 0

        opportunity = 0.0
        emotion: str | None = None
        if (
            self.backchannel_pause_min_ms
            <= self.current_pause_ms
            <= self.backchannel_pause_max_ms
        ):
            opportunity = 0.85
            emotion = "thinking"

        self.last_state = vad_result["state"]
        return {
            "frame_id": frame.frame_id,
            "timestamp_ms": frame.timestamp_ms,
            "energy": vad_result["rms"],
            "is_speaking": is_speaking,
            "pause_ms": self.current_pause_ms,
            "backchannel_opportunity": opportunity,
            "barge_in_score": 0.6 if is_speaking else 0.0,
            "emotion": emotion,
        }

    def to_event(self, session_id: str, features: dict[str, Any]) -> Event:
        return Event(
            session_id=session_id,
            type=AUDIO_FEATURE_UPDATE,
            source="audio_feature_extractor",
            timestamp_ms=features["timestamp_ms"],
            payload=features,
        )
