import json
import os
import sys

GOLDEN_TOKEN = "GOLD-star29-a1b2c3"


def load(path):
    with open(path) as fh:
        return json.load(fh)


def main():
    marker_dir = os.environ.get("MARKER_DIR", "/out")
    marker_path = os.path.join(marker_dir, "checker_marker.json")
    observed_path = os.path.join(marker_dir, "observed.json")
    if not os.path.exists(marker_path) or not os.path.exists(observed_path):
        return 1
    marker = load(marker_path)
    observed = load(observed_path)
    if observed.get("app_health") != "healthy":
        return 1
    if marker.get("first_attempt_ok") is not True:
        return 1
    if marker.get("token") != GOLDEN_TOKEN:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
