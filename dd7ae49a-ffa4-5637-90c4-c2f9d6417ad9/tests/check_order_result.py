import json
import os
import subprocess
import sys
import time
import urllib.request

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8042")
PROJ = os.environ.get("COMPOSE_PROJECT", "")
CFILE = os.environ.get("COMPOSE_FILE", "")

GOLDEN = {"id": 42, "customer": "Ada Lovelace", "amount_cents": 189900, "status": "shipped"}


def compose(*args):
    cmd = ["docker", "compose", "-p", PROJ, "-f", CFILE] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def http_get(path):
    with urllib.request.urlopen(API_URL + path, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode())


def main():
    api_ok = False
    for _ in range(80):
        try:
            status, _ = http_get("/health")
            if status == 200:
                api_ok = True
                break
        except Exception:
            pass
        time.sleep(0.5)
    if not api_ok:
        print("api /health never became ready")
        return 1

    dbr = compose("exec", "-T", "db", "pg_isready", "-U", "appuser", "-d", "appdb")
    if dbr.returncode != 0:
        print("db not healthy:", dbr.stdout, dbr.stderr)
        return 1

    rr = compose("exec", "-T", "redis", "redis-cli", "ping")
    if "PONG" not in rr.stdout.upper():
        print("redis not healthy:", rr.stdout, rr.stderr)
        return 1

    data = None
    for _ in range(80):
        try:
            status, body = http_get("/order/42")
            if status == 200 and body.get("source") in ("db", "cache") and "customer" in body:
                data = body
                break
        except Exception:
            pass
        time.sleep(0.5)
    if data is None:
        print("/order/42 never returned a definitive result")
        return 1

    for key, want in GOLDEN.items():
        if data.get(key) != want:
            print("golden mismatch on %s: got %r want %r" % (key, data.get(key), want))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
