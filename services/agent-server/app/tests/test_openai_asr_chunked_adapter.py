from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from asr import ASRProviderConfig
from asr.openai_asr import OpenAIChunkedASRAdapter, OpenAIRealtimeASRAdapter
from audio_input import AudioFrame


class FakeTranscriptions:
    def __init__(self, text: object = "你好") -> None:
        self.calls: list[dict[str, object]] = []
        self.text = text

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.text


class FakeOpenAIClient:
    def __init__(self, text: object = {"text": "你好"}) -> None:
        self.transcriptions = FakeTranscriptions(text)
        self.audio = SimpleNamespace(transcriptions=self.transcriptions)


def make_config(**updates) -> ASRProviderConfig:
    data = {
        "provider": "openai",
        "api_key": "test-key",
        "model": "gpt-4o-mini-transcribe",
        "chunk_duration_ms": 100,
        "min_chunk_duration_ms": 50,
        "sample_rate": 16000,
        "channels": 1,
    }
    data.update(updates)
    return ASRProviderConfig(**data)


def make_frame(samples: int = 800) -> AudioFrame:
    return AudioFrame(
        session_id="s1",
        sample_rate=16000,
        channels=1,
        samples_per_channel=samples,
        pcm=b"\x01\x00" * samples,
    )


def test_openai_chunked_start_missing_key() -> None:
    adapter = OpenAIChunkedASRAdapter(ASRProviderConfig(provider="openai"))

    with pytest.raises(ValueError, match="OpenAI ASR config is incomplete"):
        asyncio.run(adapter.start_stream("s1"))


def test_openai_chunked_fake_client_transcription_success() -> None:
    client = FakeOpenAIClient({"text": "你好"})
    adapter = OpenAIChunkedASRAdapter(make_config(), client=client)

    async def run():
        await adapter.start_stream("s1")
        return await adapter.send_audio(make_frame(samples=1600))

    results = asyncio.run(run())

    assert results[0].text == "你好"
    assert results[0].is_final is True
    call = client.transcriptions.calls[0]
    assert call["model"] == "gpt-4o-mini-transcribe"
    assert call["file"].name == "audio.wav"


def test_openai_chunked_waits_until_chunk_duration() -> None:
    adapter = OpenAIChunkedASRAdapter(
        make_config(chunk_duration_ms=200),
        client=FakeOpenAIClient({"text": "done"}),
    )

    async def run():
        await adapter.start_stream("s1")
        first = await adapter.send_audio(make_frame(samples=800))
        second = await adapter.send_audio(make_frame(samples=2400))
        return first, second

    first, second = asyncio.run(run())

    assert first == []
    assert second[0].text == "done"


def test_openai_chunked_flush_sends_remaining_buffer() -> None:
    adapter = OpenAIChunkedASRAdapter(
        make_config(chunk_duration_ms=500, min_chunk_duration_ms=50),
        client=FakeOpenAIClient({"text": "flush text"}),
    )

    async def run():
        await adapter.start_stream("s1")
        await adapter.send_audio(make_frame(samples=1600))
        return await adapter.flush()

    results = asyncio.run(run())

    assert results[0].text == "flush text"


def test_openai_chunked_close_clears_buffer() -> None:
    adapter = OpenAIChunkedASRAdapter(make_config(), client=FakeOpenAIClient())

    async def run():
        await adapter.start_stream("s1")
        await adapter.send_audio(make_frame(samples=800))
        await adapter.close()

    asyncio.run(run())

    assert adapter.closed is True
    assert adapter.buffer == []


def test_extract_text_from_response_variants() -> None:
    adapter = OpenAIChunkedASRAdapter(make_config())

    assert adapter._extract_text_from_response({"text": "dict"}) == "dict"
    assert adapter._extract_text_from_response(SimpleNamespace(text="object")) == "object"
    assert adapter._extract_text_from_response("plain") == "plain"


def test_build_transcription_kwargs_omits_none() -> None:
    adapter = OpenAIChunkedASRAdapter(make_config(openai_prompt=None, openai_temperature=None))
    file = SimpleNamespace(name="audio.wav")

    kwargs = adapter._build_transcription_kwargs(file)

    assert kwargs["file"] is file
    assert "prompt" not in kwargs
    assert "temperature" not in kwargs


def test_openai_chunked_status_masks_key_and_realtime_alias_imports() -> None:
    adapter = OpenAIChunkedASRAdapter(make_config(api_key="secret-key"))
    status = adapter.get_status().model_dump(mode="python")

    assert status["metadata"]["mode"] == "chunked_transcription"
    assert "secret-key" not in str(status)
    assert issubclass(OpenAIRealtimeASRAdapter, OpenAIChunkedASRAdapter)


def test_openai_sdk_missing_error_is_clear(monkeypatch) -> None:
    adapter = OpenAIChunkedASRAdapter(make_config(), client=None)

    def fail_import() -> object:
        raise RuntimeError("OpenAI SDK is not installed. Install openai to enable real ASR.")

    monkeypatch.setattr(adapter, "_create_openai_client", fail_import)

    with pytest.raises(RuntimeError, match="OpenAI SDK is not installed"):
        asyncio.run(adapter._transcribe_wav_bytes(b"RIFFfakeWAVE"))
