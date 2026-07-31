import os
import sys


def main():
    run_rc = os.environ.get("RUN_RC", "")
    uid = os.environ.get("UID_OBSERVED", "")
    marker = os.environ.get("FILE_MARKER", "")
    payload = os.environ.get("FILE_PAYLOAD_OK", "")
    if run_rc != "0":
        return 1
    if uid != "1000":
        return 1
    if payload != "1":
        return 1
    if marker != "1":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
