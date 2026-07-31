import json
import os
import sys

GOLDEN = {"service": "server", "sum": 385, "token": "2f6063993261e912"}


def main():
    marker_dir = os.environ.get("MARKER_DIR", "")
    path = os.path.join(marker_dir, "marker.json")
    if not marker_dir or not os.path.isfile(path):
        sys.stderr.write("no client success marker at %s\n" % path)
        return 1
    try:
        got = json.load(open(path))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("marker unreadable: %s\n" % exc)
        return 1
    if got != GOLDEN:
        sys.stderr.write("marker payload mismatch: %r != %r\n" % (got, GOLDEN))
        return 1
    sys.stdout.write("connectivity OK: client fetched golden payload by name\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
