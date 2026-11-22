"""A tiny local HTTP server used only by tests to exercise the real
PlaywrightCollector machinery (navigation, waits, robots.txt, HTTP-status
handling, block detection) without ever touching a live retailer site."""
from __future__ import annotations

import http.server
import threading
from pathlib import Path


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (stdlib method name)
        path = self.path.split("?")[0]
        routes: dict[str, str] = getattr(self.server, "routes", {})
        status_routes: dict[str, int] = getattr(self.server, "status_routes", {})
        fixtures_dir: Path = self.server.fixtures_dir
        disallow_paths: list[str] = getattr(self.server, "disallow_paths", [])

        if path == "/robots.txt":
            self._serve_robots(disallow_paths)
        elif path in status_routes:
            self.send_response(status_routes[path])
            self.end_headers()
        elif path in routes:
            self._serve_file(fixtures_dir / routes[path])
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_robots(self, disallow_paths: list[str]) -> None:
        lines = ["User-agent: *"]
        lines += [f"Disallow: {p}" for p in disallow_paths] or ["Disallow:"]
        body = "\n".join(lines).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass  # silence default request logging to stderr


class LocalSiteServer:
    """`routes` maps an exact request path (no query string) to a fixture
    filename under `fixtures_dir`. `status_routes` maps a path to a bare
    HTTP status code (e.g. 403) with no body — for testing HTTP-status
    block handling."""

    def __init__(
        self,
        fixtures_dir: Path,
        routes: dict[str, str] | None = None,
        status_routes: dict[str, int] | None = None,
    ) -> None:
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.fixtures_dir = fixtures_dir
        self.httpd.routes = routes or {}
        self.httpd.status_routes = status_routes or {}
        self.httpd.disallow_paths = []
        self.port = self.httpd.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def set_disallow_paths(self, paths: list[str]) -> None:
        self.httpd.disallow_paths = paths
