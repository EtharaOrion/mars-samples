#!/usr/bin/env python3
"""credential-rotator daemon.

Every ROTATION_INTERVAL_SECONDS: generate new URL-safe token, ALTER USER
app PASSWORD via postgres superuser DSN, SET current_app_password in
redis, append audit line to rotator log. First rotation fires immediately
on startup so D2 readiness gates can succeed within seconds.
"""
from __future__ import annotations

import configparser
import datetime
import hashlib
import secrets
import sys
import time

import psycopg2
import redis


def load_config(path: str = "/etc/rotator/rotator.conf") -> dict:
    p = configparser.ConfigParser()
    p.read(path)
    return {
        "rotation_interval_seconds": p.getint("rotator", "rotation_interval_seconds"),
        "postgres_superuser_dsn": p.get("rotator", "postgres_superuser_dsn"),
        "redis_host": p.get("rotator", "redis_host"),
        "redis_port": p.getint("rotator", "redis_port"),
        "redis_key": p.get("rotator", "redis_key"),
        "audit_log_path": p.get("rotator", "audit_log_path"),
    }


def main() -> int:
    cfg = load_config()
    r = redis.Redis(host=cfg["redis_host"], port=cfg["redis_port"], decode_responses=True)
    rotation_index = 0
    while True:
        rotation_index += 1
        new_password = secrets.token_urlsafe(24)
        try:
            with psycopg2.connect(cfg["postgres_superuser_dsn"]) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"ALTER USER app PASSWORD %s", (new_password,))
            r.set(cfg["redis_key"], new_password)
            digest = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            with open(cfg["audit_log_path"], "a") as fh:
                fh.write(f"{now} rotation_index={rotation_index} new_password_digest_sha256={digest}\n")
        except Exception as exc:
            print(f"rotation {rotation_index} failed: {exc}", file=sys.stderr, flush=True)
        time.sleep(cfg["rotation_interval_seconds"])


if __name__ == "__main__":
    sys.exit(main())
