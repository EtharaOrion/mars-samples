"""Fail unless the freshly built report artifact exists with the golden bytes.

This is part of the project's own test target so that `make test` genuinely
depends on `make build` having run first with the correct environment. If the
artifact is missing (wrong job order) or has the wrong version (env not in
scope), this exits non-zero and the whole workflow fails.
"""
import os
import sys

from calc.buildreport import render

ART = os.path.join("out", "app.txt")


def main():
    if not os.path.exists(ART):
        sys.stderr.write("missing build artifact: " + ART + "\n")
        return 1
    with open(ART, "r", encoding="utf-8") as fh:
        got = fh.read()
    want = render() + "\n"
    if got != want:
        sys.stderr.write("artifact content mismatch\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
