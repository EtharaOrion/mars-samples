import hashlib
import json
import os
import sys
import urllib.request

FROZEN = {
    "Dockerfile": "11b73f14d93d88fec797d62984135b95fda6c180bc47a200cbd4cc4f5fd0db78",
    "widget.py": "6d81cd6ef371156bdc9df43ec8a866a00243c3540688142828ecaa624f801374",
}


def main():
    ref = os.environ.get("IMAGE_REF", "localhost:5050/widgetapp:v1")
    port = os.environ.get("REGISTRY_PORT", "5050")
    app_dir = os.environ.get("APP_DIR", "")

    host = ref.split("/")[0]
    if host != "localhost:%s" % port:
        sys.stderr.write("image ref host is not the local registry: %s\n" % host)
        return 1

    try:
        with urllib.request.urlopen(
            "http://localhost:%s/v2/_catalog" % port, timeout=5
        ) as resp:
            repos = json.loads(resp.read().decode()).get("repositories") or []
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("local registry not reachable at localhost:%s: %s\n" % (port, exc))
        return 1
    if "widgetapp" not in repos:
        sys.stderr.write("widgetapp not served by the local registry\n")
        return 1

    if not app_dir:
        sys.stderr.write("APP_DIR not provided for integrity check\n")
        return 1
    for rel, want in FROZEN.items():
        p = os.path.join(app_dir, rel)
        if not os.path.isfile(p):
            sys.stderr.write("frozen app file missing: %s\n" % p)
            return 1
        got = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if got != want:
            sys.stderr.write("RED LINE: %s modified (%s != %s)\n" % (rel, got, want))
            return 1

    sys.stdout.write("offline + integrity OK: localhost-only registry, app source frozen\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
