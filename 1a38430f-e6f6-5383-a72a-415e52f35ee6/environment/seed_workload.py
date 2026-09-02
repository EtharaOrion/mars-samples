#!/usr/bin/env python3
"""Deterministic redis keyspace seed for redis-single-service-silent-config-
drift (inv-24).

Populates three namespaces via inline RESP2 pipelining over the unix socket:
  app:session:0001 .. app:session:0100  (100 keys)
  app:cache:0001   .. app:cache:0150    (150 keys)
  app:counter:0001 .. app:counter:0050  (50 keys)

Every value is derived from the integer index by pinned string formatting so
the seed produces byte-identical output on every image build.  No wall-clock
reads, no randomness, no environment reads.  Reads the socket path from an
optional env var REDIS_SOCK; defaults to /var/run/redis/redis.sock.
"""
from __future__ import annotations

import os
import socket
import sys


SOCK_PATH = os.environ.get("REDIS_SOCK", "/var/run/redis/redis.sock")


def _resp_set(key: str, val: str) -> bytes:
    k = key.encode("ascii")
    v = val.encode("ascii")
    return (
        b"*3\r\n"
        b"$3\r\nSET\r\n"
        + f"${len(k)}\r\n".encode("ascii") + k + b"\r\n"
        + f"${len(v)}\r\n".encode("ascii") + v + b"\r\n"
    )


def main() -> int:
    frames = []
    for i in range(1, 101):
        frames.append(_resp_set(f"app:session:{i:04d}",
                                f"session_token_{i:04d}_deadbeef"))
    for i in range(1, 151):
        frames.append(_resp_set(f"app:cache:{i:04d}",
                                f"cached_value_{i:04d}_cafefeed"))
    for i in range(1, 51):
        frames.append(_resp_set(f"app:counter:{i:04d}",
                                str(i * 137)))

    payload = b"".join(frames)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(15.0)
    s.connect(SOCK_PATH)
    s.sendall(payload)

    # Drain +OK replies (one per SET) so redis flushes them and closes cleanly.
    remaining = len(frames)
    buf = b""
    while remaining > 0:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
        remaining -= buf.count(b"+OK\r\n")
        buf = buf.rsplit(b"+OK\r\n", 1)[-1]

    s.close()
    print(f"seed_workload: wrote {len(frames)} keys")
    return 0


if __name__ == "__main__":
    sys.exit(main())
