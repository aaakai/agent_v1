from __future__ import annotations

from tools import livekit_worker


def test_livekit_worker_dry_run_prints_safe_config(monkeypatch, capsys) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret-value")
    monkeypatch.setenv("LIVEKIT_ROOM", "room")

    exit_code = livekit_worker.main(["--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"api_secret": "***"' in captured.out
    assert "secret-value" not in captured.out
    assert "room" in captured.out
    assert "worker_options" in captured.out
    assert "safe_asr_config" in captured.out


def test_livekit_worker_dry_run_accepts_options(monkeypatch, capsys) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret-value")

    exit_code = livekit_worker.main(
        [
            "--dry-run",
            "--room",
            "room-override",
            "--identity",
            "agent-override",
            "--duration",
            "1",
            "--no-runtime-consumers",
            "--sample-rate",
            "24000",
            "--channels",
            "2",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "room-override" in captured.out
    assert "agent-override" in captured.out
    assert "24000" in captured.out
    assert "secret-value" not in captured.out


def test_livekit_worker_dry_run_accepts_asr_options(monkeypatch, capsys) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret-value")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    exit_code = livekit_worker.main(
        [
            "--dry-run",
            "--asr-provider",
            "openai",
            "--asr-language",
            "zh",
            "--asr-model",
            "gpt-4o-mini-transcribe",
            "--asr-chunk-ms",
            "1000",
            "--asr-min-chunk-ms",
            "300",
            "--asr-max-buffer-ms",
            "3000",
            "--asr-silence-flush-ms",
            "700",
            "--asr-min-speech-ms",
            "100",
            "--asr-max-turn-ms",
            "9000",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"provider": "openai"' in captured.out
    assert '"configured": true' in captured.out
    assert '"chunk_duration_ms": 1000' in captured.out
    assert '"min_chunk_duration_ms": 300' in captured.out
    assert '"asr_silence_flush_ms": 700' in captured.out
    assert '"asr_max_turn_ms": 9000' in captured.out
    assert "gpt-4o-mini-transcribe" in captured.out
    assert "openai-secret" not in captured.out


def test_livekit_worker_dry_run_disable_asr(monkeypatch, capsys) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret-value")

    exit_code = livekit_worker.main([
        "--dry-run",
        "--disable-asr",
        "--no-asr-flush-on-silence",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"provider": "disabled"' in captured.out
    assert '"asr_enabled": false' in captured.out
    assert '"asr_flush_on_silence": false' in captured.out


def test_livekit_worker_rejects_incomplete_config(monkeypatch, capsys) -> None:
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)

    exit_code = livekit_worker.main([])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "LiveKit config is incomplete" in captured.err


def test_livekit_worker_non_dry_run_returns_error_without_traceback(monkeypatch, capsys) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret-value")

    async def fail_run_worker(_options):
        raise RuntimeError("LiveKit Python SDK is not installed")

    monkeypatch.setattr(livekit_worker, "run_worker", fail_run_worker)

    exit_code = livekit_worker.main(["--duration", "0.01"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "Traceback" not in captured.err
    assert "secret-value" not in captured.err
