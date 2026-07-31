import hashlib
import json
import os
import re
import subprocess
import sys

PROJ = os.environ.get("COMPOSE_PROJECT", "")
CFILE = os.environ.get("COMPOSE_FILE", "")
APP_DIR = os.environ.get("APP_DIR", "")
TESTDIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = "/data"
ANON_NAME = re.compile(r"^[0-9a-f]{64}$")


def compose(*args):
    cmd = ["docker", "compose", "-p", PROJ, "-f", CFILE] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    ps = compose("ps", "-q", "app")
    cid = ps.stdout.strip().splitlines()[0].strip() if ps.stdout.strip() else ""
    if not cid:
        print("app container not running:", ps.stdout, ps.stderr)
        return 1

    ins = subprocess.run(
        ["docker", "inspect", "-f", "{{json .Mounts}}", cid],
        capture_output=True, text=True,
    )
    if ins.returncode != 0:
        print("docker inspect failed:", ins.stderr)
        return 1
    try:
        mounts = json.loads(ins.stdout.strip() or "[]")
    except Exception as exc:
        print("could not parse mounts:", exc)
        return 1

    data_mount = None
    for m in mounts:
        if m.get("Destination") == DATA_PATH:
            data_mount = m
            break
    if data_mount is None:
        print("no mount at %s; mounts=%r" % (DATA_PATH, mounts))
        return 1
    if data_mount.get("Type") != "volume":
        print("mount at %s is not a volume: %r" % (DATA_PATH, data_mount))
        return 1
    name = data_mount.get("Name") or ""
    if not name or ANON_NAME.match(name):
        print("mount at %s is not a NAMED volume (name=%r)" % (DATA_PATH, name))
        return 1

    # Red line RL1: application source + image build must be byte-identical.
    for line in open(os.path.join(TESTDIR, "shas.txt")):
        line = line.strip()
        if not line:
            continue
        want, rel = line.split()
        got = hashlib.sha256(open(os.path.join(APP_DIR, rel), "rb").read()).hexdigest()
        if got != want:
            print("red line violated: %s changed" % rel)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
