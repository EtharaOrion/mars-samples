import json
import os
import sys


def _list(name):
    raw = os.environ.get(name, "") or "[]"
    try:
        val = json.loads(raw)
    except Exception:
        return []
    return val if isinstance(val, list) else []


def main():
    readonly = os.environ.get("READONLY", "") == "true"
    uid = os.environ.get("UID_OBSERVED", "")
    capdrop = [str(c).upper() for c in _list("CAPDROP")]
    capadd = _list("CAPADD")
    nonewpriv = os.environ.get("NONEWPRIV", "") == "true"
    src_sha = os.environ.get("SRC_SHA", "")
    expected_sha = os.environ.get("EXPECTED_SHA", "")

    if not readonly:
        sys.stderr.write("read-only rootfs not set\n")
        return 1
    if uid in ("", "-1"):
        sys.stderr.write("effective uid unresolved (app not running non-root)\n")
        return 1
    try:
        if int(uid) == 0:
            sys.stderr.write("running as root (uid 0)\n")
            return 1
    except ValueError:
        return 1
    if "ALL" not in capdrop:
        sys.stderr.write("cap-drop ALL missing: %r\n" % capdrop)
        return 1
    if len(capadd) > 1:
        sys.stderr.write("too many caps added back: %r\n" % capadd)
        return 1
    if not nonewpriv:
        sys.stderr.write("no-new-privileges missing\n")
        return 1
    if not expected_sha or src_sha != expected_sha:
        sys.stderr.write("RL1: app source sha changed (expected %r got %r)\n" % (expected_sha, src_sha))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
