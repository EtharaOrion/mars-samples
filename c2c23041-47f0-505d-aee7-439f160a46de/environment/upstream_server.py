#!/usr/bin/env python3
"""Deterministic upstream stub for the nginx-mtls-forward-auth task.

Listens on 127.0.0.1:8080. Serves the reference index.html on GET / and
echoes the incoming request header block as text/plain on GET
/_echo_headers so the verifier can inspect the X-Verified-Subject value
nginx forwarded from $ssl_client_s_dn.
"""

from __future__ import annotations

import http.server
import socketserver
import sys
from pathlib import Path

INDEX_PATH = Path("/opt/upstream/index.html")


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            body = INDEX_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/_echo_headers":
            lines = []
            for k, v in self.headers.items():
                lines.append(f"{k}: {v}")
            body = ("\n".join(lines) + "\n").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


def main() -> int:
    with socketserver.TCPServer(("127.0.0.1", 8080), Handler) as httpd:
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
