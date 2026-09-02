#!/usr/bin/env python3
import http.server
import json
import os
import random
import socketserver
import threading
import time

from prometheus_client import CollectorRegistry, Counter, CONTENT_TYPE_LATEST, generate_latest

BIND_HOST = "127.0.0.1"
BIND_PORT = 8080
AUDIT_LOG_PATH = "/var/log/app/audit.log"

CANONICAL_ROUTES = ("/api/list", "/api/get", "/api/put", "/health")
CANONICAL_STATUSES = ("200", "400", "500")

REGISTRY = CollectorRegistry(auto_describe=False)
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests processed by route and status.",
    ["route", "status"],
    registry=REGISTRY,
)

_state_lock = threading.Lock()
_mutation = {"armed": False, "salt": 0}


def _arm_mutation():
    with _state_lock:
        _mutation["armed"] = True
        _mutation["salt"] = random.randint(1, 2**30)


threading.Timer(9.0, _arm_mutation).start()


def _labels_for(route: str, status: str) -> dict:
    with _state_lock:
        if _mutation["armed"]:
            suffix = f"?_={_mutation['salt']}-{random.randint(0, 10_000_000)}"
            return {"route": route + suffix, "status": status}
    return {"route": route, "status": status}


def _append_audit(route: str, status: str) -> None:
    ts_ms = int(time.time() * 1000)
    line = json.dumps(
        {"ts": ts_ms, "route": route, "status": status},
        sort_keys=True,
        separators=(",", ":"),
    )
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _record(route: str, status: str) -> None:
    HTTP_REQUESTS.labels(**_labels_for(route, status)).inc()
    _append_audit(route, status)


def _traffic_worker() -> None:
    rng = random.Random(0xC0FFEE)
    while True:
        route = rng.choice(CANONICAL_ROUTES)
        status = rng.choice(CANONICAL_STATUSES)
        try:
            _record(route, status)
        except Exception:
            pass
        time.sleep(0.05)


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args, **_kwargs):
        return

    def do_GET(self):
        if self.path == "/metrics":
            body = generate_latest(REGISTRY)
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


class _ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    if not os.path.exists(AUDIT_LOG_PATH):
        open(AUDIT_LOG_PATH, "a", encoding="utf-8").close()
    threading.Thread(target=_traffic_worker, daemon=True).start()
    with _ThreadedServer((BIND_HOST, BIND_PORT), _Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
