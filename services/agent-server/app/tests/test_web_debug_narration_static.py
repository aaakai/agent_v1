from __future__ import annotations

from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "web_debug" / "static"


def test_index_html_contains_narration_and_short_timeline() -> None:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    assert 'id="narrationBox"' in html
    assert 'id="shortTimelineList"' in html
    assert "本次发生了什么" in html
    assert "简短链路" in html


def test_app_js_renders_narration_and_short_timeline() -> None:
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "renderNarration" in app_js
    assert "renderShortTimeline" in app_js
    assert "narration" in app_js
    assert "short_timeline" in app_js


def test_style_css_contains_narration_and_short_timeline_styles() -> None:
    style = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    assert ".narration" in style
    assert ".short-timeline" in style
    assert ".timeline-step" in style
