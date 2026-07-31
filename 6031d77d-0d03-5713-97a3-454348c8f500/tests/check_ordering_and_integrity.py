import json
import os
import sys

FROZEN_APP_SHA = "c2c9d12c3488c9d590bbd5b43103648ac6ef20522b562a06c7a47347c3d35c41"
FROZEN_CHECKER_SHA = "8b9704b823a4d41d1ae85df17b251c8225aa86779431b2f5b1485b2044e88a08"


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
    if observed.get("app_sha") != FROZEN_APP_SHA:
        return 1
    if observed.get("checker_sha") != FROZEN_CHECKER_SHA:
        return 1
    if marker.get("attempts") != 1:
        return 1
    if marker.get("first_attempt_ok") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
