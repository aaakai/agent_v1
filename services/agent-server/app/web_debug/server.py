from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from web_debug.api import list_scenarios, run_debug_scenario  # noqa: E402
from web_debug.livekit_api import (  # noqa: E402
    create_debug_token,
    get_debug_state,
    get_livekit_config_status,
    reset_debug_state,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

try:  # pragma: no cover - availability depends on the local environment.
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, RedirectResponse
except Exception:  # noqa: BLE001 - optional dependency.
    FastAPI = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    FileResponse = None  # type: ignore[assignment]
    RedirectResponse = None  # type: ignore[assignment]


def create_app() -> Any:
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed; use run_dev_server fallback")

    app = FastAPI(title="Lulula Web Debug Panel")

    @app.get("/")
    def root() -> Any:
        return RedirectResponse(url="/debug")

    @app.get("/api/scenarios")
    def scenarios() -> dict[str, Any]:
        return list_scenarios()

    @app.post("/api/run-scenario")
    def run_scenario(body: dict[str, Any]) -> dict[str, Any]:
        try:
            return run_debug_scenario(
                scenario=str(body.get("scenario", "full")),
                with_player=bool(body.get("with_player", True)),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/livekit/config")
    def livekit_config() -> dict[str, Any]:
        return get_livekit_config_status()

    @app.post("/api/livekit/token")
    def livekit_token(body: dict[str, Any]) -> dict[str, Any]:
        try:
            return create_debug_token(
                body,
                allow_mock=bool(body.get("allow_mock", False)),
            )
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/livekit/state")
    def livekit_state() -> dict[str, Any]:
        return get_debug_state()

    @app.post("/api/livekit/reset")
    def livekit_reset() -> dict[str, Any]:
        return reset_debug_state()

    @app.get("/debug")
    def debug_panel() -> Any:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    @app.get("/livekit-debug")
    def livekit_debug_panel() -> Any:
        return FileResponse(STATIC_DIR / "livekit_debug.html", media_type="text/html")

    @app.get("/static/app.js")
    def app_js() -> Any:
        return FileResponse(STATIC_DIR / "app.js", media_type="text/javascript")

    @app.get("/static/style.css")
    def style_css() -> Any:
        return FileResponse(STATIC_DIR / "style.css", media_type="text/css")

    @app.get("/static/livekit_debug.js")
    def livekit_debug_js() -> Any:
        return FileResponse(
            STATIC_DIR / "livekit_debug.js",
            media_type="text/javascript",
        )

    @app.get("/static/livekit_debug.css")
    def livekit_debug_css() -> Any:
        return FileResponse(STATIC_DIR / "livekit_debug.css", media_type="text/css")

    return app


def run_dev_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    print(f"Debug panel: http://{host}:{port}/debug")
    try:
        import uvicorn  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001 - optional dependency.
        _run_fallback_server(host=host, port=port)
        return

    if FastAPI is None:
        _run_fallback_server(host=host, port=port)
        return
    uvicorn.run(create_app(), host=host, port=port)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Lulula web debug panel.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = argv if argv is not None else sys.argv[1:]
    if "--help" in args or "-h" in args:
        parser.print_help()
        return 0
    parsed = parser.parse_args(args)
    run_dev_server(host=parsed.host, port=parsed.port)
    return 0


class _FallbackHandler(BaseHTTPRequestHandler):
    server_version = "LululaWebDebug/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook name.
        path = urlparse(self.path).path
        if path == "/":
            self._send_redirect("/debug")
            return
        if path == "/api/scenarios":
            self._send_json(list_scenarios())
            return
        if path == "/api/livekit/config":
            self._send_json(get_livekit_config_status())
            return
        if path == "/api/livekit/state":
            self._send_json(get_debug_state())
            return
        if path == "/debug":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/livekit-debug":
            self._send_file(
                STATIC_DIR / "livekit_debug.html",
                "text/html; charset=utf-8",
            )
            return
        if path == "/static/app.js":
            self._send_file(STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
            return
        if path == "/static/style.css":
            self._send_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            return
        if path == "/static/livekit_debug.js":
            self._send_file(
                STATIC_DIR / "livekit_debug.js",
                "text/javascript; charset=utf-8",
            )
            return
        if path == "/static/livekit_debug.css":
            self._send_file(
                STATIC_DIR / "livekit_debug.css",
                "text/css; charset=utf-8",
            )
            return
        self._send_error(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook name.
        path = urlparse(self.path).path
        if path == "/api/livekit/reset":
            self._send_json(reset_debug_state())
            return

        if path not in {"/api/run-scenario", "/api/livekit/token"}:
            self._send_error(HTTPStatus.NOT_FOUND, "not found")
            return

        try:
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body)
            if path == "/api/run-scenario":
                data = run_debug_scenario(
                    scenario=str(payload.get("scenario", "full")),
                    with_player=bool(payload.get("with_player", True)),
                )
            else:
                data = create_debug_token(
                    payload,
                    allow_mock=bool(payload.get("allow_mock", False)),
                )
        except (RuntimeError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json(data)

    def log_message(self, format: str, *args: Any) -> None:
        return None

    def _send_json(
        self,
        data: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._send_error(HTTPStatus.NOT_FOUND, "not found")
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
        self.send_header("location", location)
        self.end_headers()

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message}, status=status)


def _run_fallback_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), _FallbackHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
