from __future__ import annotations

from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "web_debug" / "static"


def test_index_html_has_simplified_summary_and_advanced_json() -> None:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    assert 'id="headlineBox"' in html
    assert 'id="outcomeBox"' in html
    assert 'id="keyDecisionsList"' in html
    assert 'id="advancedJson"' in html
    assert "<details" in html
    assert "Advanced JSON" in html
    assert "Speech Lane" in html
    assert "SFX Lane" in html
    assert "Ambience Lane" in html
    assert "/static/app.js" in html
    assert "/static/style.css" in html


def test_app_js_uses_simplified_summary_renderer() -> None:
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "renderSummary" in app_js
    assert "simplified_summary" in app_js
    assert "advancedJson" in app_js
    assert "/api/scenarios" in app_js
    assert "/api/run-scenario" in app_js


def test_style_css_contains_summary_timeline_and_warning_styles() -> None:
    style = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    assert ".summary-card" in style
    assert ".lane-card" in style
    assert ".warning" in style
    assert ".timeline" in style
    assert ".status-playing" in style
