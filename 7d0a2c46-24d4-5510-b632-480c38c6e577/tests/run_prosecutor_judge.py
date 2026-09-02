"""Harness-provided prosecutor judge stub.

The real 3-judge Claude council runs on the host in harness/mars_council.py
against the trajectory artifacts Harbor pulls out of this container. This
in-container stub exists solely so G-VER-INVARIANCE and legacy test.sh
invocations that reference /tests/run_prosecutor_judge.py have a parser
to target. It is deterministic, produces no reward, and defers judging
to the harness-side council.

Emits a machine-readable marker to stdout; exit 0.
"""
import json
import sys


def main() -> int:
    result = {
        "reward": None,
        "note": "harness_provided",
        "delegate": "harness/mars_council.py",
        "reason": "prosecutor judge runs on host via 3-model Claude council; in-container stub deferred",
    }
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
