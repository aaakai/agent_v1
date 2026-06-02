from __future__ import annotations

import pytest

from web_debug import server


def test_create_app_is_importable() -> None:
    assert callable(server.create_app)


def test_server_main_help_returns_zero(capsys) -> None:
    exit_code = server.main(["--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Run the Lulula web debug panel" in captured.out


def test_tool_web_debug_server_help_returns_zero(capsys) -> None:
    from tools import web_debug_server

    exit_code = web_debug_server.main(["--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--port" in captured.out


def test_fastapi_routes_if_available() -> None:
    pytest.importorskip("fastapi")
    testclient = pytest.importorskip("fastapi.testclient")

    client = testclient.TestClient(server.create_app())

    scenarios = client.get("/api/scenarios")
    assert scenarios.status_code == 200
    assert any(item["name"] == "sfx" for item in scenarios.json()["scenarios"])

    run = client.post(
        "/api/run-scenario",
        json={"scenario": "sfx", "with_player": True},
    )
    assert run.status_code == 200
    assert run.json()["playback_state"]["sfx"]["active"]
    assert run.json()["simplified_summary"]["headline"]
    assert run.json()["simplified_summary"]["narration"]

    debug = client.get("/debug")
    assert debug.status_code == 200
    assert "Lulula Agentic Voice Runtime Debug Panel" in debug.text
    assert "Summary" in debug.text

    app_js = client.get("/static/app.js")
    assert app_js.status_code == 200
    assert "/api/run-scenario" in app_js.text

    style_css = client.get("/static/style.css")
    assert style_css.status_code == 200
    assert "body" in style_css.text
