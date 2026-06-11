from __future__ import annotations

import asyncio

import pytest

from asr import ASRProviderConfig
from asr.funasr_asr import FunASRASRAdapter


def test_funasr_adapter_missing_endpoint_status() -> None:
    adapter = FunASRASRAdapter(ASRProviderConfig(provider="funasr"))

    assert adapter.get_status().provider == "funasr"
    assert adapter.get_status().configured is False
    with pytest.raises(ValueError, match="funasr ASR config is incomplete"):
        asyncio.run(adapter.start_stream("s1"))


def test_sensevoice_adapter_endpoint_configured() -> None:
    adapter = FunASRASRAdapter(
        ASRProviderConfig(provider="sensevoice", endpoint="http://127.0.0.1:10095")
    )

    status = adapter.get_status()

    assert status.provider == "sensevoice"
    assert status.configured is True
