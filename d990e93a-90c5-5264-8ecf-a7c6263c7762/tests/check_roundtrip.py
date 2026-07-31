import json
import os
import subprocess
import sys
import urllib.request

GOLDEN = "widgetapp v1 ready sum=129 checksum=9d7ebb2376e0ff03"


def _http(path):
    port = os.environ.get("REGISTRY_PORT", "5050")
    url = "http://localhost:%s%s" % (port, path)
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.status, resp.read().decode()


def _docker(args):
    return subprocess.run(["docker"] + args, capture_output=True, text=True, check=False)


def main():
    ref = os.environ.get("IMAGE_REF", "localhost:5050/widgetapp:v1")

    try:
        _, body = _http("/v2/_catalog")
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("registry catalog unreachable: %s\n" % exc)
        return 1
    repos = json.loads(body).get("repositories") or []
    if "widgetapp" not in repos:
        sys.stderr.write("repo 'widgetapp' absent from catalog: %s\n" % body)
        return 1

    try:
        _, body = _http("/v2/widgetapp/tags/list")
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("tags/list unreachable: %s\n" % exc)
        return 1
    tags = json.loads(body).get("tags") or []
    if "v1" not in tags:
        sys.stderr.write("tag 'v1' absent from tags/list: %s\n" % body)
        return 1

    rmi = _docker(["rmi", "-f", ref])
    if rmi.returncode != 0:
        sys.stderr.write("could not remove local image before pull: %s\n" % rmi.stderr)
        return 1
    if _docker(["image", "inspect", ref]).returncode == 0:
        sys.stderr.write("local image still present after rmi: %s\n" % ref)
        return 1

    pull = _docker(["pull", ref])
    if pull.returncode != 0:
        sys.stderr.write("fresh pull from local registry failed: %s\n" % pull.stderr)
        return 1

    run = _docker(["run", "--rm", ref])
    if run.returncode != 0:
        sys.stderr.write("run of pulled image failed: %s\n" % run.stderr)
        return 1
    out = run.stdout.strip()
    if out != GOLDEN:
        sys.stderr.write("golden mismatch: %r != %r\n" % (out, GOLDEN))
        return 1

    sys.stdout.write("roundtrip OK: pushed, pulled fresh, ran to golden\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
