"""Emit the deterministic build report consumed as the graded artifact.

Run as: python3 -m calc.buildreport  (writes report to stdout)
The APP_VERSION environment variable is embedded in the header line, so the
report is only correct when the workflow exports APP_VERSION at a scope the
build step can see.
"""
import os

from calc.core import square, sum_squares, checksum


def render():
    version = os.environ.get("APP_VERSION", "0.0.0")
    values = list(range(1, 11))
    lines = [
        "app-report v" + version,
        "sum_squares(1..10)=" + str(sum_squares(values)),
        "square(12)=" + str(square(12)),
        "checksum=" + str(checksum(values)),
        "status=ok",
    ]
    return "\n".join(lines)


def main():
    print(render())


if __name__ == "__main__":
    main()
