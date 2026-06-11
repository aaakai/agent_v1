from __future__ import annotations

from asr import ASRProviderConfig
from asr.factory import create_asr_adapter
from asr.openai_asr import OpenAIChunkedASRAdapter


def test_factory_openai_returns_chunked_adapter() -> None:
    adapter = create_asr_adapter(
        ASRProviderConfig(provider="openai", api_key="key")
    )

    assert isinstance(adapter, OpenAIChunkedASRAdapter)


def test_factory_openai_missing_key_still_creates_adapter() -> None:
    adapter = create_asr_adapter(ASRProviderConfig(provider="openai"))

    assert isinstance(adapter, OpenAIChunkedASRAdapter)
    assert adapter.get_status().configured is False
