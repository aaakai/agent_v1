from __future__ import annotations

import importlib
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .config import LiveKitConfig


class LiveKitTokenRequest(BaseModel):
    room_name: str
    identity: str
    name: str | None = None
    can_publish: bool = True
    can_subscribe: bool = True
    ttl_seconds: int = 3600

    @field_validator("room_name", "identity")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value


class LiveKitTokenResponse(BaseModel):
    url: str
    token: str
    room_name: str
    identity: str
    expires_in: int
    metadata: dict[str, Any] = Field(default_factory=dict)


def create_livekit_token(
    config: LiveKitConfig,
    request: LiveKitTokenRequest,
) -> LiveKitTokenResponse:
    _ensure_configured(config)
    api = _load_livekit_api()

    token = api.AccessToken(config.api_key, config.api_secret)
    if hasattr(token, "with_identity"):
        token = token.with_identity(request.identity)
    if request.name and hasattr(token, "with_name"):
        token = token.with_name(request.name)
    if hasattr(token, "with_ttl"):
        token = token.with_ttl(timedelta(seconds=request.ttl_seconds))

    grants = api.VideoGrants(
        room_join=True,
        room=request.room_name,
        can_publish=request.can_publish,
        can_subscribe=request.can_subscribe,
    )
    if hasattr(token, "with_grants"):
        token = token.with_grants(grants)
    else:
        raise RuntimeError("LiveKit SDK token API is not supported")

    jwt = token.to_jwt() if hasattr(token, "to_jwt") else None
    if not isinstance(jwt, str) or not jwt:
        raise RuntimeError("LiveKit SDK did not produce a token")

    return LiveKitTokenResponse(
        url=config.url or "",
        token=jwt,
        room_name=request.room_name,
        identity=request.identity,
        expires_in=request.ttl_seconds,
        metadata={"mock": False},
    )


def create_dev_mock_token(
    config: LiveKitConfig,
    request: LiveKitTokenRequest,
) -> LiveKitTokenResponse:
    return LiveKitTokenResponse(
        url=config.url or "ws://localhost:7880",
        token=f"mock-token-for-{request.identity}-in-{request.room_name}",
        room_name=request.room_name,
        identity=request.identity,
        expires_in=request.ttl_seconds,
        metadata={"mock": True},
    )


def create_token(
    config: LiveKitConfig,
    request: LiveKitTokenRequest,
    allow_mock: bool = False,
) -> LiveKitTokenResponse:
    _ensure_configured(config)
    if allow_mock:
        try:
            return create_livekit_token(config, request)
        except RuntimeError:
            return create_dev_mock_token(config, request)
    return create_livekit_token(config, request)


def _ensure_configured(config: LiveKitConfig) -> None:
    if not config.is_configured():
        raise ValueError("LiveKit config is incomplete")


def _load_livekit_api() -> Any:
    try:
        module = _import_external_livekit_api()
    except Exception as exc:  # noqa: BLE001 - normalize SDK absence.
        raise RuntimeError("LiveKit SDK is not installed") from exc
    if not hasattr(module, "AccessToken") or not hasattr(module, "VideoGrants"):
        raise RuntimeError("LiveKit SDK is not installed")
    return module


def _import_external_livekit_api() -> Any:
    app_dir = str(Path(__file__).resolve().parents[1])
    saved_path = list(sys.path)
    saved_livekit = sys.modules.pop("livekit", None)
    saved_livekit_api = sys.modules.pop("livekit.api", None)
    try:
        sys.path = [path for path in sys.path if str(Path(path or ".").resolve()) != app_dir]
        return importlib.import_module("livekit.api")
    finally:
        sys.path = saved_path
        if saved_livekit is not None:
            sys.modules["livekit"] = saved_livekit
        if saved_livekit_api is not None:
            sys.modules["livekit.api"] = saved_livekit_api
