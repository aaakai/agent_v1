from __future__ import annotations

import asyncio

import pytest

from asr import ASRProviderConfig
from asr.deepgram_asr import DeepgramASRAdapter


def test_deepgram_adapter_missing_config_start_error() -> None:
    adapter = DeepgramASRAdapter(ASRProviderConfig(provider="deepgram"))

    assert adapter.get_status().provider == "deepgram"
    assert adapter.get_status().configured is False
    with pytest.raises(ValueError, match="Deepgram ASR config is incomplete"):
        asyncio.run(adapter.start_stream("s1"))


def test_deepgram_adapter_configured_skeleton_no_secret() -> None:
    adapter = DeepgramASRAdapter(
        ASRProviderConfig(provider="deepgram", api_key="deep-secret")
    )

    status = adapter.get_status().model_dump(mode="python")

    assert status["configured"] is True
    assert "deep-secret" not in str(status)
