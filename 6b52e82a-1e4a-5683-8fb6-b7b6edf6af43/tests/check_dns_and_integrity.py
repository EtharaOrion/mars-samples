import hashlib
import json
import os
import subprocess
import sys

FROZEN = {
    "server/server.py": "0ecc780c5beecb63ffa9e9b873df9087bbc880d3563857cc6943e32af5c25a02",
    "client/client.py": "80b9c02d2dd3f84be017970e7c3bc70bf0fa2e4d82efa2bfc02f7f19894ee64e",
}


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _docker(args):
    return subprocess.run(
        ["docker"] + args, capture_output=True, text=True, check=False
    )


def _cid(project, service):
    r = _docker([
        "ps", "-aq",
        "--filter", "label=com.docker.compose.project=" + project,
        "--filter", "label=com.docker.compose.service=" + service,
    ])
    ids = [x for x in r.stdout.split() if x]
    return ids[0] if ids else ""


def _networks(cid):
    r = _docker(["inspect", "-f", "{{json .NetworkSettings.Networks}}", cid])
    try:
        return set(json.loads(r.stdout).keys())
    except Exception:  # noqa: BLE001
        return set()


def check_integrity(app_dir):
    for rel, want in FROZEN.items():
        p = os.path.join(app_dir, rel)
        if not os.path.isfile(p):
            sys.stderr.write("frozen source missing: %s\n" % p)
            return False
        got = _sha(p)
        if got != want:
            sys.stderr.write("RED LINE: %s modified (%s != %s)\n" % (rel, got, want))
            return False
    return True


def check_shared_userdefined(project):
    sc = _cid(project, "server")
    cc = _cid(project, "client")
    if not sc or not cc:
        sys.stderr.write("containers not found for project %s\n" % project)
        return False
    shared = _networks(sc) & _networks(cc)
    shared = {n for n in shared if n not in ("bridge", "host", "none")}
    if not shared:
        sys.stderr.write("no shared user-defined network between client and server\n")
        return False
    for name in shared:
        r = _docker(["network", "inspect", "-f", "{{.Driver}}", name])
        if r.stdout.strip() == "bridge":
            sys.stdout.write("dns OK: client+server share user-defined bridge '%s'\n" % name)
            return True
    sys.stderr.write("shared network is not a user-defined bridge\n")
    return False


def main():
    app_dir = os.environ.get("BUNDLE_APP", "")
    project = os.environ.get("COMPOSE_PROJECT", "")
    if not check_integrity(app_dir):
        return 1
    if not check_shared_userdefined(project):
        return 1
    sys.stdout.write("integrity + name-based resolution evidence OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
