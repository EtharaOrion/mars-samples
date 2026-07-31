import json
import os
import sys
import urllib.request

BASE = os.environ.get("APP_URL", "http://127.0.0.1:8000")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode())


def main():
    status, health = get("/health")
    if status != 200 or health.get("status") != "ok":
        return 1
    status, c5 = get("/compute?n=5")
    if status != 200 or c5.get("result") != 26:
        return 1
    status, c8 = get("/compute?n=8")
    if status != 200 or c8.get("result") != 39:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
