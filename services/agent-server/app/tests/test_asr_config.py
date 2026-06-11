from __future__ import annotations

from asr import ASRProviderConfig


def clear_asr_env(monkeypatch) -> None:
    for name in [
        "ASR_PROVIDER",
        "ASR_LANGUAGE",
        "ASR_SAMPLE_RATE",
        "ASR_CHANNELS",
        "ASR_MODEL",
        "ASR_ENDPOINT",
        "ASR_API_KEY",
        "ASR_API_SECRET",
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
        "FUNASR_ENDPOINT",
        "SENSEVOICE_ENDPOINT",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_asr_config_defaults_to_mock(monkeypatch) -> None:
    clear_asr_env(monkeypatch)

    config = ASRProviderConfig.from_env()

    assert config.provider == "mock"
    assert config.language == "zh"
    assert config.is_configured() is True


def test_openai_config_reads_openai_key(monkeypatch) -> None:
    clear_asr_env(monkeypatch)
    monkeypatch.setenv("ASR_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    config = ASRProviderConfig.from_env()

    assert config.api_key == "openai-secret"
    assert config.model == "gpt-4o-mini-transcribe"
    assert config.is_configured() is True
    assert "openai-secret" not in str(config.to_safe_dict())


def test_asr_config_reads_chunk_env(monkeypatch) -> None:
    clear_asr_env(monkeypatch)
    monkeypatch.setenv("ASR_CHUNK_DURATION_MS", "1200")
    monkeypatch.setenv("ASR_MIN_CHUNK_DURATION_MS", "400")
    monkeypatch.setenv("ASR_MAX_BUFFER_DURATION_MS", "4000")
    monkeypatch.setenv("OPENAI_ASR_RESPONSE_FORMAT", "json")
    monkeypatch.setenv("OPENAI_ASR_PROMPT", "中文技术对话")
    monkeypatch.setenv("OPENAI_ASR_TEMPERATURE", "0.2")

    config = ASRProviderConfig.from_env()

    assert config.chunk_duration_ms == 1200
    assert config.min_chunk_duration_ms == 400
    assert config.max_buffer_duration_ms == 4000
    assert config.openai_prompt == "中文技术对话"
    assert config.openai_temperature == 0.2
    assert config.to_safe_dict()["chunk_duration_ms"] == 1200


def test_asr_config_provider_override_can_fill_env_credentials(monkeypatch) -> None:
    clear_asr_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    config = ASRProviderConfig.from_env().model_copy(
        update={"provider": "openai"}
    ).with_env_credentials()

    assert config.is_configured() is True
    assert config.api_key == "openai-secret"


def test_deepgram_config_reads_deepgram_key(monkeypatch) -> None:
    clear_asr_env(monkeypatch)
    monkeypatch.setenv("ASR_PROVIDER", "deepgram")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "deepgram-secret")

    config = ASRProviderConfig.from_env()

    assert config.api_key == "deepgram-secret"
    assert config.missing_fields() == []
    assert "deepgram-secret" not in str(config.to_safe_dict())


def test_funasr_config_reads_endpoint(monkeypatch) -> None:
    clear_asr_env(monkeypatch)
    monkeypatch.setenv("ASR_PROVIDER", "funasr")
    monkeypatch.setenv("FUNASR_ENDPOINT", "http://127.0.0.1:10095")

    config = ASRProviderConfig.from_env()

    assert config.endpoint == "http://127.0.0.1:10095"
    assert config.is_configured() is True


def test_asr_config_missing_fields_and_disabled(monkeypatch) -> None:
    clear_asr_env(monkeypatch)
    assert ASRProviderConfig(provider="openai").missing_fields() == ["api_key"]
    assert ASRProviderConfig(provider="funasr").missing_fields() == ["endpoint"]
    assert ASRProviderConfig(provider="disabled").is_configured() is True
