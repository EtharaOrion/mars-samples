#!/usr/bin/env python3
"""Verifier-invoked driver for inv-29.

Invokes bash /workspace/get_password.sh before each of --n UPDATEs (10s
apart). Captures per-UPDATE JSON to /tmp/driver_output.json plus audit
lines to /var/log/driver/driver.log. Emits apply_updates_ok=true on
success. Verifies distinct-password threshold and rotator-liveness after
all iterations complete.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import time

import psycopg2

sys.path.insert(0, "/etc/app")
import config as cfg  # type: ignore


ROTATOR_LOG_LINE_RE = re.compile(
    r"^(?P<ts>\S+)\s+rotation_index=(?P<idx>\d+)\s+new_password_digest_sha256=(?P<digest>[0-9a-f]{64})\s*$"
)


def parse_rotator_log() -> list[dict]:
    lines: list[dict] = []
    try:
        with open(cfg.ROTATOR_AUDIT_LOG) as fh:
            for line in fh:
                m = ROTATOR_LOG_LINE_RE.match(line.rstrip("\n"))
                if m:
                    lines.append(m.groupdict())
    except FileNotFoundError:
        pass
    return lines


def latest_rotation_index_before(ts_iso: str) -> int:
    lines = parse_rotator_log()
    idx = 0
    for line in lines:
        if line["ts"] <= ts_iso:
            idx = int(line["idx"])
    return idx


def audit(msg: str) -> None:
    with open(cfg.DRIVER_AUDIT_LOG, "a") as fh:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        fh.write(f"{now} {msg}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    args = parser.parse_args()

    if args.n != 4:
        print(f"driver expects --n 4, got {args.n}", file=sys.stderr)
        return 2

    updates: list[dict] = []
    for i in range(args.n):
        target_customer_id = cfg.TARGET_ROWS[i]
        call_ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

        proc = subprocess.run(
            ["bash", cfg.GET_PASSWORD_SCRIPT],
            capture_output=True, text=True,
            timeout=cfg.GET_PASSWORD_TIMEOUT_SECONDS,
        )
        password = proc.stdout.splitlines()[0] if proc.stdout else ""
        password_digest = hashlib.sha256(password.encode("utf-8")).hexdigest()

        current_rotation_index = latest_rotation_index_before(call_ts)

        record = {
            "iteration": i + 1,
            "call_wall_clock": call_ts,
            "captured_password": password,
            "captured_password_digest": password_digest,
            "current_rotation_index_at_call": current_rotation_index,
            "target_customer_id": target_customer_id,
        }

        try:
            with psycopg2.connect(
                host=cfg.POSTGRES_HOST, port=cfg.POSTGRES_PORT,
                user=cfg.POSTGRES_USER, dbname=cfg.POSTGRES_DB, password=password,
                connect_timeout=5,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE customer_records SET last_reconciled_window = %s, "
                        "updated_at = now(), updated_by = %s WHERE customer_id = %s "
                        "RETURNING last_reconciled_window",
                        (current_rotation_index, "apply_updates.py", target_customer_id),
                    )
                    row = cur.fetchone()
                    record["update_returned_window"] = row[0] if row else None
                    record["exception"] = None
        except Exception as exc:
            record["exception"] = f"{type(exc).__name__}: {exc}"
            audit(f"UPDATE {i+1} failed: {record['exception']}")
            updates.append(record)
            with open(cfg.DRIVER_OUTPUT_JSON, "w") as fh:
                json.dump({"updates": updates, "status": "failed"}, fh, indent=2)
            print(f"UPDATE {i+1} failed: {record['exception']}", file=sys.stderr)
            return 3

        audit(f"UPDATE {i+1} ok: rotation_index={current_rotation_index} row={target_customer_id}")
        updates.append(record)

        if i < args.n - 1:
            time.sleep(cfg.INTER_UPDATE_SLEEP_SECONDS)

    digests = [u["captured_password_digest"] for u in updates]
    distinct_count = len(set(digests))
    if distinct_count < cfg.MIN_DISTINCT_PASSWORDS:
        audit(f"get_password_stale_output_detected distinct={distinct_count}")

    lines = parse_rotator_log()
    if lines:
        first_idx = int(lines[0]["idx"])
        last_idx = int(lines[-1]["idx"])
        advance = last_idx - first_idx + 1
        if advance < cfg.MIN_ROTATIONS_WITHIN_HORIZON:
            audit(f"rotator_frozen_or_stopped advance={advance}")

    with open(cfg.DRIVER_OUTPUT_JSON, "w") as fh:
        json.dump({"updates": updates, "status": "ok"}, fh, indent=2)

    print("apply_updates_ok=true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
