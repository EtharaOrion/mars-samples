import json
import os
import sys
import time
import urllib.request

TARGET = "http://server:8000/data"
OUT = "/out/marker.json"


def fetch():
    with urllib.request.urlopen(TARGET, timeout=3) as resp:
        return resp.read()


def main():
    last = ""
    for _ in range(40):
        try:
            raw = fetch()
            payload = json.loads(raw.decode())
            os.makedirs("/out", exist_ok=True)
            with open(OUT, "w") as fh:
                json.dump(payload, fh, sort_keys=True)
            sys.stdout.write("resolved server by name; marker written\n")
            return 0
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            time.sleep(1)
    sys.stderr.write("failed to reach server by name: %s\n" % last)
    return 1


if __name__ == "__main__":
    sys.exit(main())
