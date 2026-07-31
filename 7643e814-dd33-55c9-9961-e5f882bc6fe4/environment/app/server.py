import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

DATA_DIR = os.environ.get("DATA_DIR", "/data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")


def ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def read_state():
    try:
        with open(STATE_FILE) as fh:
            return json.load(fh)
    except Exception:
        return {"value": None, "writes": 0}


def write_state(state):
    ensure_dir()
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, sort_keys=True)
    os.replace(tmp, STATE_FILE)


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, obj):
        body = json.dumps(obj, sort_keys=True).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            self.reply(200, {"status": "ok"})
            return
        if path == "/get":
            state = read_state()
            self.reply(200, {"value": state.get("value"), "writes": int(state.get("writes", 0))})
            return
        if path == "/put":
            value = parse_qs(parsed.query).get("value", [""])[0]
            state = read_state()
            state = {"value": value, "writes": int(state.get("writes", 0)) + 1}
            write_state(state)
            self.reply(200, {"stored": value, "writes": state["writes"]})
            return
        self.reply(404, {"error": "not found"})

    def log_message(self, *args):
        return


def main():
    ensure_dir()
    if not os.path.exists(STATE_FILE):
        write_state({"value": None, "writes": 0})
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
