import os
import sys


def main():
    invoker = os.environ.get("INVOKER_UID", "")
    privileged = os.environ.get("PRIVILEGED", "")
    src_sha = os.environ.get("WORKLOAD_SHA", "")
    expected_sha = os.environ.get("EXPECTED_SHA", "")
    if invoker != "1000":
        return 1
    if privileged != "0":
        return 1
    if not expected_sha or src_sha != expected_sha:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
