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


def test_livekit_worker_rejects_incomplete_config(monkeypatch, capsys) -> None:
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)

    exit_code = livekit_worker.main([])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "LiveKit config is incomplete" in captured.err
