#!/usr/bin/env python3
"""Minimal HTTP server for HF Space healthcheck / anti-sleep ping."""
from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

START = time.time()
PORT = int(os.environ.get("PORT", os.environ.get("APP_PORT", "7860")))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/health", "/healthz"):
            cookie_ok = os.path.isfile("/data/cookie.json")
            self._send(
                200,
                {
                    "service": "ncmm-hf",
                    "status": "ok",
                    "uptime_sec": int(time.time() - START),
                    "cookie_present": cookie_ok,
                    "hint": "cron runs inside container; ping / to reduce free-tier sleep",
                },
            )
            return
        if self.path == "/run/musician":
            self._send(
                200,
                {
                    "ok": False,
                    "message": "use cron or: ncmm -c /data/config.yaml musician",
                },
            )
            return
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[keepalive] listening on 0.0.0.0:{PORT}", flush=True)
    server.serve_forever()
