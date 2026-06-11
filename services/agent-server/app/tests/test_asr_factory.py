from __future__ import annotations

import pytest

from asr import ASRProviderConfig, MockStreamingASRAdapter
from asr.deepgram_asr import DeepgramASRAdapter
from asr.factory import DisabledASRAdapter, create_asr_adapter, create_asr_adapter_from_env
from asr.funasr_asr import FunASRASRAdapter
from asr.openai_asr import OpenAIChunkedASRAdapter


def test_factory_creates_mock_streaming_adapter() -> None:
    adapter = create_asr_adapter(ASRProviderConfig(provider="mock"))

    assert isinstance(adapter, MockStreamingASRAdapter)


def test_factory_creates_disabled_adapter() -> None:
    adapter = create_asr_adapter(ASRProviderConfig(provider="disabled"))

    assert isinstance(adapter, DisabledASRAdapter)
    assert adapter.get_status().streaming is False


def test_factory_creates_provider_skeletons() -> None:
    assert isinstance(
        create_asr_adapter(ASRProviderConfig(provider="openai", api_key="key")),
        OpenAIChunkedASRAdapter,
    )
    assert isinstance(
        create_asr_adapter(ASRProviderConfig(provider="deepgram", api_key="key")),
        DeepgramASRAdapter,
    )
    assert isinstance(
        create_asr_adapter(ASRProviderConfig(provider="funasr", endpoint="http://local")),
        FunASRASRAdapter,
    )


def test_factory_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="Unknown ASR provider"):
        create_asr_adapter(ASRProviderConfig(provider="wat"))


def test_factory_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "disabled")

    adapter = create_asr_adapter_from_env()

    assert isinstance(adapter, DisabledASRAdapter)
