from __future__ import annotations

from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "web_debug" / "static"


def test_index_html_contains_required_debug_panel_elements() -> None:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    assert "Lulula Agentic Voice Runtime Debug Panel" in html
    assert 'id="scenarioSelect"' in html
    assert "/static/app.js" in html
    assert "/static/style.css" in html


def test_app_js_calls_debug_apis_and_renders_json() -> None:
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "fetch('/api/scenarios')" in app_js or 'fetch("/api/scenarios")' in app_js
    assert "/api/run-scenario" in app_js
    assert "JSON.stringify" in app_js
    assert "speechLane" in app_js


def test_style_css_contains_basic_layout_styles() -> None:
    style = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    assert "body" in style
    assert ".lane" in style
    assert ".card" in style
    assert "pre" in style
