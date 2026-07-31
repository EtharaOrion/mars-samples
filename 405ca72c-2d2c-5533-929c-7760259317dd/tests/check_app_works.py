import json
import os
import sys

EXPECTED_RESULT = 77
EXPECTED_SERVICE = "star30"


def main():
    code = os.environ.get("APP_CODE", "")
    body = os.environ.get("APP_BODY", "")
    if code != "200":
        sys.stderr.write("app not serving golden response: code=%r\n" % code)
        return 1
    try:
        data = json.loads(body)
    except Exception as exc:
        sys.stderr.write("app body not json: %s\n" % exc)
        return 1
    if data.get("status") != "ok":
        return 1
    if data.get("result") != EXPECTED_RESULT:
        sys.stderr.write("wrong result: %r\n" % data.get("result"))
        return 1
    if data.get("service") != EXPECTED_SERVICE:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
