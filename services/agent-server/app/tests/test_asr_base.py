from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from asr import (
    ASRProviderConfig,
    ASRProviderStatus,
    ASRResult,
    BaseASRAdapter,
    DeepgramASRAdapter,
    FunASRASRAdapter,
    OpenAIRealtimeASRAdapter,
)
from audio_input import AudioFrame


def test_asr_result_final_defaults_stability_to_one() -> None:
    result = ASRResult(session_id="session-1", text="done", is_final=True)

    assert result.stability == 1.0
    assert result.metadata == {}


def test_asr_result_allows_empty_text() -> None:
    result = ASRResult(session_id="session-1", text="", is_final=False)

    assert result.text == ""
    assert result.stability == 0.0


def test_asr_result_requires_session_id() -> None:
    with pytest.raises(ValidationError):
        ASRResult(text="hello", is_final=False)


def test_base_asr_adapter_defaults_to_empty_results() -> None:
    adapter = BaseASRAdapter()
    frame = AudioFrame(session_id="session-1")

    async def run() -> tuple[list[ASRResult], list[ASRResult]]:
        await adapter.start_stream("session-1")
        sent = await adapter.send_audio(frame)
        received = await adapter.receive_results()
        await adapter.close()
        return sent, received

    assert asyncio.run(run()) == ([], [])
    assert adapter.get_status().configured is False


def test_asr_provider_status_is_json_friendly() -> None:
    status = ASRProviderStatus(provider="mock", configured=True)

    assert status.model_dump(mode="python")["provider"] == "mock"


@pytest.mark.parametrize(
    "adapter",
    [
        DeepgramASRAdapter(ASRProviderConfig(provider="deepgram", api_key="key")),
        FunASRASRAdapter(ASRProviderConfig(provider="funasr", endpoint="http://local")),
    ],
)
def test_non_openai_provider_placeholders_raise_not_implemented(adapter: BaseASRAdapter) -> None:
    with pytest.raises(NotImplementedError, match="not implemented yet"):
        asyncio.run(adapter.start_stream("session-1"))


def test_openai_realtime_alias_starts_chunked_adapter() -> None:
    adapter = OpenAIRealtimeASRAdapter(ASRProviderConfig(provider="openai", api_key="key"))

    asyncio.run(adapter.start_stream("session-1"))

    assert adapter.get_status().metadata["mode"] == "chunked_transcription"
