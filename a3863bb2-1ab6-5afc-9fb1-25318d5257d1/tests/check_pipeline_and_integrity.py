import hashlib
import os
import subprocess
import sys

GOLDEN = "NESTED-OK sum=70 sha=1dc225e4bf52ce88"

FROZEN = {
    "nested/Dockerfile": "79a0e38f1f98daa59ecfb5ae4c7fc36b8e6ee19151d246f5475a80bd8528aea1",
    "nested/compute.sh": "f17a1bc044de706d587cd6338c1e8857b83e98ef2fbf9bf0a7413e2040cabcbf",
    "nested/values.txt": "1dc225e4bf52ce888147d7cc22f9561dab49ced1fb27ef3f00f1064c6c084326",
}


def _docker(args):
    return subprocess.run(["docker"] + args, capture_output=True, text=True, check=False)


def main():
    image = os.environ.get("NESTED_IMAGE", "star26-nested:v1")
    name = os.environ.get("NESTED_NAME", "star26-nested-ctr")
    out_dir = os.environ.get("OUT_DIR", "./out")
    app_dir = os.environ.get("APP_DIR", "")

    # A nested IMAGE must have been built (evidence of the build half of the chain).
    if _docker(["image", "inspect", image]).returncode != 0:
        sys.stderr.write("nested image %r was never built\n" % image)
        return 1

    # The nested container must have been created FROM that nested image
    # (proves build -> run chaining, not a bare command run).
    insp = _docker(["inspect", "-f", "{{.Config.Image}}", name])
    if insp.returncode != 0:
        sys.stderr.write("nested container %r absent\n" % name)
        return 1
    if insp.stdout.strip() != image:
        sys.stderr.write("nested container not from nested image: %r\n" % insp.stdout.strip())
        return 1

    # The captured marker must equal golden.
    marker = os.path.join(out_dir, "result.txt")
    if not os.path.isfile(marker):
        sys.stderr.write("marker missing: %s\n" % marker)
        return 1
    got = open(marker).read().strip()
    if got != GOLDEN:
        sys.stderr.write("marker golden mismatch: %r != %r\n" % (got, GOLDEN))
        return 1

    # RED LINE: nested app source + its Dockerfile are byte-frozen.
    if not app_dir:
        sys.stderr.write("APP_DIR not provided for integrity check\n")
        return 1
    for rel, want in FROZEN.items():
        p = os.path.join(app_dir, rel)
        if not os.path.isfile(p):
            sys.stderr.write("frozen file missing: %s\n" % p)
            return 1
        got = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if got != want:
            sys.stderr.write("RED LINE: %s modified (%s != %s)\n" % (rel, got, want))
            return 1

    sys.stdout.write("pipeline chain + integrity OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
