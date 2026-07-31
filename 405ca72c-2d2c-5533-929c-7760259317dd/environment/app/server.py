import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

CACHE_DIR = "/var/cache/app"
STATE = os.path.join(CACHE_DIR, "state.json")
COEFFS = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
SERVICE = "star30"


def init_state():
    result = sum(COEFFS[:8])
    with open(STATE, "w") as fh:
        json.dump({"result": result, "service": SERVICE}, fh, sort_keys=True)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, sort_keys=True).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok"})
            return
        if self.path.startswith("/compute"):
            try:
                with open(STATE) as fh:
                    st = json.load(fh)
            except Exception:
                self._send(500, {"status": "error"})
                return
            self._send(200, {"status": "ok", "result": st["result"], "service": st["service"]})
            return
        self._send(404, {"status": "not_found"})

    def log_message(self, *args):
        return


def main():
    init_state()
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()


if __name__ == "__main__":
    main()
