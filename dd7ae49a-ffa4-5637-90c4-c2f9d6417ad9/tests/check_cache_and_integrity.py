import hashlib
import json
import os
import subprocess
import sys
import urllib.request

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8042")
PROJ = os.environ.get("COMPOSE_PROJECT", "")
CFILE = os.environ.get("COMPOSE_FILE", "")
APP_DIR = os.environ.get("APP_DIR", "")
TESTDIR = os.path.dirname(os.path.abspath(__file__))


def compose(*args):
    cmd = ["docker", "compose", "-p", PROJ, "-f", CFILE] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def http_get(path):
    with urllib.request.urlopen(API_URL + path, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode())


def main():
    # Prime the cache, then the immediately following read must be a cache hit.
    try:
        http_get("/order/42")
    except Exception as exc:
        print("priming call failed:", exc)
        return 1
    try:
        status, body = http_get("/order/42")
    except Exception as exc:
        print("second call failed:", exc)
        return 1
    if status != 200 or body.get("source") != "cache":
        print("expected cache hit, got:", body)
        return 1

    kr = compose("exec", "-T", "redis", "redis-cli", "EXISTS", "order:42")
    if kr.stdout.strip() != "1":
        print("redis key order:42 missing:", kr.stdout, kr.stderr)
        return 1

    # Red line: app source + seed SQL must be byte-identical.
    for line in open(os.path.join(TESTDIR, "shas.txt")):
        line = line.strip()
        if not line:
            continue
        want, rel = line.split()
        got = hashlib.sha256(open(os.path.join(APP_DIR, rel), "rb").read()).hexdigest()
        if got != want:
            print("red line violated: %s changed" % rel)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
