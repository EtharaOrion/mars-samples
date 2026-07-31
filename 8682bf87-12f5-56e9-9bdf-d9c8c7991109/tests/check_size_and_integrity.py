import hashlib
import os
import sys

SIZE_THRESHOLD_BYTES = 100000000

GOLDEN_SHA256 = {
    "go.mod": "1c3b299d53a88a9f1f26fbeea27a250adf494dcb85a575eac21e57e8dd99fa6c",
    "main.go": "dca8aadb5f657056b593aa5f91ce143bec68e1f0f38540994aafe4e5cf91a00d",
    "data/table.txt": "e6d78aea101dc2eb47305efad5d86813c97a3006a0e4df971e2c9544d9a847dd",
}


def main():
    try:
        size = int(os.environ["IMAGE_SIZE_BYTES"])
    except (KeyError, ValueError):
        return 1
    if size >= SIZE_THRESHOLD_BYTES:
        return 1
    src = os.environ.get("SRC_DIR", "/grade/src")
    for rel, want in GOLDEN_SHA256.items():
        path = os.path.join(src, rel)
        try:
            with open(path, "rb") as fh:
                got = hashlib.sha256(fh.read()).hexdigest()
        except OSError:
            return 1
        if got != want:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
