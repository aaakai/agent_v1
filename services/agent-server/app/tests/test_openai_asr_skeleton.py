from __future__ import annotations

import asyncio

import pytest

from asr import ASRProviderConfig
from asr.openai_asr import OpenAIRealtimeASRAdapter
from audio_input import AudioFrame


def test_openai_adapter_missing_config_status_and_start_error() -> None:
    adapter = OpenAIRealtimeASRAdapter(ASRProviderConfig(provider="openai"))

    assert adapter.get_status().provider == "openai"
    assert adapter.get_status().configured is False
    with pytest.raises(ValueError, match="OpenAI ASR config is incomplete"):
        asyncio.run(adapter.start_stream("s1"))


def test_openai_adapter_configured_skeleton_does_not_leak_key() -> None:
    adapter = OpenAIRealtimeASRAdapter(
        ASRProviderConfig(provider="openai", api_key="secret-key")
    )

    status = adapter.get_status().model_dump(mode="python")

    assert status["configured"] is True
    assert "secret-key" not in str(status)
    with pytest.raises(RuntimeError, match="ASR stream is not started"):
        asyncio.run(adapter.send_audio(AudioFrame(session_id="s1")))
