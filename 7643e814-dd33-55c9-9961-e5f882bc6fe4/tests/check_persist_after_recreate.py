import json
import os
import subprocess
import sys
import time
import urllib.request

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8080")
PROJ = os.environ.get("COMPOSE_PROJECT", "")
CFILE = os.environ.get("COMPOSE_FILE", "")

GOLDEN = "star24-golden-8f2ad1"


def compose(*args):
    cmd = ["docker", "compose", "-p", PROJ, "-f", CFILE] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def http_get(path):
    with urllib.request.urlopen(API_URL + path, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode())


def wait_health(label):
    for _ in range(80):
        try:
            status, _ = http_get("/health")
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    print("api /health never became ready (%s)" % label)
    return False


def main():
    if not wait_health("initial"):
        return 1

    try:
        status, body = http_get("/put?value=" + GOLDEN)
    except Exception as exc:
        print("put failed:", exc)
        return 1
    if status != 200 or body.get("stored") != GOLDEN:
        print("put did not store golden:", body)
        return 1

    try:
        status, s1 = http_get("/get")
    except Exception as exc:
        print("first get failed:", exc)
        return 1
    if status != 200 or s1.get("value") != GOLDEN or s1.get("writes") != 1:
        print("state S1 wrong before recreate:", s1)
        return 1

    # Temporal boundary: destroy and recreate the containers WITHOUT removing volumes.
    down = compose("down")
    if down.returncode != 0:
        print("compose down failed:", down.stdout, down.stderr)
        return 1
    up = compose("up", "-d")
    if up.returncode != 0:
        print("compose up (recreate) failed:", up.stdout, up.stderr)
        return 1

    if not wait_health("after-recreate"):
        return 1

    s2 = None
    for _ in range(80):
        try:
            status, body = http_get("/get")
            if status == 200:
                s2 = body
                break
        except Exception:
            pass
        time.sleep(0.5)
    if s2 is None:
        print("/get never returned after recreate")
        return 1

    if s2.get("value") != GOLDEN:
        print("persistence lost: after recreate value=%r want %r" % (s2.get("value"), GOLDEN))
        return 1
    if s2.get("writes") != 1:
        print("write count not preserved after recreate:", s2)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
