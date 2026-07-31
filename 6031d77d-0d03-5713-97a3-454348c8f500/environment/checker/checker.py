import json
import os
import urllib.request

OUT_PATH = "/out/checker_marker.json"
APP_URL = "http://app:8000/"


def one_attempt():
    try:
        with urllib.request.urlopen(APP_URL, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return True, data.get("token")
    except Exception:
        return False, None


def main():
    ok, token = one_attempt()
    marker = {"first_attempt_ok": ok, "token": token, "attempts": 1}
    os.makedirs("/out", exist_ok=True)
    with open(OUT_PATH, "w") as fh:
        json.dump(marker, fh, sort_keys=True)


main()
