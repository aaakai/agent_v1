from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from asr import (
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


@pytest.mark.parametrize(
    "adapter",
    [
        OpenAIRealtimeASRAdapter(),
        DeepgramASRAdapter(),
        FunASRASRAdapter(),
    ],
)
def test_provider_placeholders_raise_not_implemented(adapter: BaseASRAdapter) -> None:
    with pytest.raises(NotImplementedError, match="not implemented yet"):
        asyncio.run(adapter.start_stream("session-1"))
