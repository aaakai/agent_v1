from __future__ import annotations

from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "web_debug" / "static"


def test_livekit_debug_static_files_exist_and_are_safe() -> None:
    html = (STATIC_DIR / "livekit_debug.html").read_text(encoding="utf-8")
    js = (STATIC_DIR / "livekit_debug.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "livekit_debug.css").read_text(encoding="utf-8")

    assert "LiveKit Debug" in html
    assert "Backend Worker Status" in html
    assert "ASR Provider Status" in html
    assert "chunked final transcription" in html
    assert "roomInput" in html
    assert "identityInput" in html
    assert "Connect" in html
    assert "/api/livekit/token" in js
    assert "/api/livekit/state" in js
    assert "/api/livekit/worker-status" in js
    assert "/api/livekit/worker-reset" in js
    assert "/api/asr/config" in js
    assert "chunk_ms" in js
    assert "API_SECRET" not in html
    assert "API_SECRET" not in js
    assert "ASR_API_KEY" not in html
    assert "ASR_API_KEY" not in js
    assert "body" in css
