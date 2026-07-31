import os
import subprocess
import sys

GOLDEN = "NESTED-OK sum=70 sha=1dc225e4bf52ce88"


def _docker(args):
    return subprocess.run(["docker"] + args, capture_output=True, text=True, check=False)


def main():
    name = os.environ.get("NESTED_NAME", "star26-nested-ctr")

    # A real nested container must exist (only a genuine `docker run` of the
    # nested image creates it). Faking the marker without a nested run fails here.
    insp = _docker(["inspect", "-f", "{{.Config.Image}}", name])
    if insp.returncode != 0:
        sys.stderr.write("nested container %r absent: %s\n" % (name, insp.stderr.strip()))
        return 1

    logs = _docker(["logs", name])
    if logs.returncode != 0:
        sys.stderr.write("cannot read nested container logs: %s\n" % logs.stderr.strip())
        return 1
    out = logs.stdout.strip()
    if out != GOLDEN:
        sys.stderr.write("nested golden mismatch: %r != %r\n" % (out, GOLDEN))
        return 1

    sys.stdout.write("nested container ran to golden\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
