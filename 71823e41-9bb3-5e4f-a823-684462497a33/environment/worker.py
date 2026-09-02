#!/usr/bin/env python3
"""FORGE inv-27 worker driver.

Invoked by the verifier as:
    python3 /opt/app/worker.py --replay --requests 1000 --workers 50 --seed 42

Reads /etc/app/config.py, connects to PgBouncer at 127.0.0.1:6432 and
Redis at 127.0.0.1:6379, runs the replay under N concurrent worker
threads, and emits `replay_ok=true` on stdout when the replay completes
without error.

The three inv-27 corruption primitives interact with this driver as
follows. P1 (pgbouncer pool_mode=transaction + psycopg2 server-side
prepared statements) surfaces as a `psycopg2.errors.InvalidSqlStatementName`
raised inside worker threads and a Postgres log line
`prepared statement "..." does not exist`. P2 (Redis SETNX cache-fill
mutex TTL=1s undersized vs the ~2-5s catalog fill duration) surfaces
as concurrent cache-fill entrants and a `stampede detected` line on
this driver's stderr. P3 (pgbouncer max_client_conn=20 vs 50 workers)
surfaces as PgBouncer log lines `login timeout` and psycopg2 connection
timeouts inside worker threads. All three primitives are recoverable
without touching worker.py: fixes go to /etc/pgbouncer/pgbouncer.ini
and /etc/app/config.py plus a pgbouncer reload.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import sys
import threading
import time
import traceback
import uuid
from typing import Any

import psycopg2
import psycopg2.errors
import redis


CONFIG_PATH = "/etc/app/config.py"


def load_config(path: str) -> Any:
    spec = importlib.util.spec_from_file_location("app_config", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load config from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_pg_connection(cfg: Any) -> Any:
    return psycopg2.connect(
        host=cfg.POSTGRES_HOST,
        port=cfg.POSTGRES_PORT,
        dbname=cfg.POSTGRES_DB,
        user=cfg.POSTGRES_USER,
        password=cfg.POSTGRES_PASSWORD,
        connect_timeout=15,
    )


def use_server_side_prepare(cfg: Any) -> bool:
    return getattr(cfg, "PSYCOPG2_PREPARE_THRESHOLD", 5) is not None


def make_redis_connection(cfg: Any) -> "redis.Redis":
    return redis.Redis(
        host=cfg.REDIS_HOST,
        port=cfg.REDIS_PORT,
        socket_connect_timeout=5,
        socket_timeout=15,
    )


def ensure_catalog_cache(rc: "redis.Redis", cfg: Any, pg_conn: Any,
                        stderr_lock: threading.Lock) -> None:
    """Guard the catalog fill behind a Redis SETNX mutex.

    Correct semantics: only one worker at a time should execute the
    catalog SELECT. Under P2 (CACHE_LOCK_TTL_SECONDS=1) the mutex
    expires while the winner is mid-fill, subsequent workers acquire
    the released lock, and multiple concurrent fills race. Stampede
    is detected by an INCR-tracked active-filler counter: if any
    worker reads a value >1 while holding the lock, that worker
    prints `stampede detected` to stderr.
    """
    cache_populated_key = "catalog:seeded_ok"
    lock_key = cfg.CACHE_LOCK_KEY
    active_key = "cache_fill:catalog:active"
    ttl = int(cfg.CACHE_LOCK_TTL_SECONDS)

    if rc.get(cache_populated_key):
        return

    acquired = rc.setnx(lock_key, os.getpid())
    if acquired:
        rc.expire(lock_key, ttl)
    if not acquired:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if rc.get(cache_populated_key):
                return
            time.sleep(0.1)
        raise TimeoutError("timed out waiting for cache fill by peer worker")

    try:
        active_count = rc.incr(active_key)
        if active_count > 1:
            with stderr_lock:
                sys.stderr.write("stampede detected\n")
                sys.stderr.flush()

        with pg_conn.cursor() as cur:
            cur.execute("SELECT catalog_id, sku, description, price, tags FROM catalog ORDER BY catalog_id")
            rows = cur.fetchall()

        rc.set(cache_populated_key, str(len(rows)), ex=3600)
    finally:
        rc.decr(active_key)
        current_owner = rc.get(lock_key)
        if current_owner is not None and current_owner.decode("ascii") == str(os.getpid()):
            rc.delete(lock_key)


def worker_thread(worker_id: int, request_ids: list[str], cfg: Any,
                  stderr_lock: threading.Lock,
                  error_bucket: list[tuple[int, BaseException]]) -> None:
    try:
        pg_conn = make_pg_connection(cfg)
        pg_conn.autocommit = False
        rc = make_redis_connection(cfg)
        prepared_this_thread = False
        use_prepare = use_server_side_prepare(cfg)

        ensure_catalog_cache(rc, cfg, pg_conn, stderr_lock)

        for request_id in request_ids:
            with pg_conn.cursor() as cur:
                cur.execute(
                    cfg.WORKER_INSERT_REQUESTS_SQL,
                    (request_id, worker_id, json.dumps({"worker": worker_id, "request": request_id})),
                )
                if use_prepare:
                    if not prepared_this_thread:
                        cur.execute(
                            "PREPARE catalog_page AS "
                            "SELECT catalog_id, sku, description, price, tags "
                            "FROM catalog WHERE catalog_id >= $1 ORDER BY catalog_id LIMIT $2"
                        )
                        prepared_this_thread = True
                    cur.execute(
                        "EXECUTE catalog_page(%s, %s)",
                        (str(uuid.UUID(int=0)), cfg.CATALOG_FETCH_BATCH_SIZE),
                    )
                else:
                    cur.execute(
                        cfg.CATALOG_QUERY,
                        (str(uuid.UUID(int=0)), cfg.CATALOG_FETCH_BATCH_SIZE),
                    )
                _ = cur.fetchall()
                cur.execute(
                    cfg.WORKER_INSERT_AUDIT_SQL,
                    (worker_id, request_id, "ok"),
                )
            pg_conn.commit()

        pg_conn.close()
        rc.close()
    except BaseException as exc:
        error_bucket.append((worker_id, exc))
        with stderr_lock:
            traceback.print_exc()


def partition_requests(total: int, workers: int, seed: int) -> list[list[str]]:
    rng = random.Random(seed)
    ids = [str(uuid.UUID(int=rng.getrandbits(128))) for _ in range(total)]
    partitions: list[list[str]] = [[] for _ in range(workers)]
    for idx, rid in enumerate(ids):
        partitions[idx % workers].append(rid)
    return partitions


def run_replay(cfg: Any, requests: int, workers: int, seed: int) -> int:
    partitions = partition_requests(requests, workers, seed)
    stderr_lock = threading.Lock()
    error_bucket: list[tuple[int, BaseException]] = []

    try:
        rc_init = make_redis_connection(cfg)
        rc_init.delete("catalog:seeded_ok", cfg.CACHE_LOCK_KEY, "cache_fill:catalog:active")
        rc_init.close()
    except Exception:
        traceback.print_exc()
        return 2

    threads = [
        threading.Thread(
            target=worker_thread,
            args=(wid, partitions[wid], cfg, stderr_lock, error_bucket),
            name=f"worker-{wid}",
        )
        for wid in range(workers)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if error_bucket:
        print("replay_ok=false", flush=True)
        return 1

    print("replay_ok=true", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="FORGE inv-27 worker driver")
    ap.add_argument("--replay", action="store_true", required=True,
                    help="run the replay against the live composition")
    ap.add_argument("--requests", type=int, default=1000,
                    help="total request count across workers")
    ap.add_argument("--workers", type=int, default=50,
                    help="concurrent worker thread count")
    ap.add_argument("--seed", type=int, default=42,
                    help="RNG seed for request-id materialization")
    args = ap.parse_args()

    cfg = load_config(CONFIG_PATH)
    if args.workers != cfg.WORKER_CONCURRENCY:
        sys.stderr.write(
            f"warning: --workers {args.workers} differs from "
            f"config WORKER_CONCURRENCY {cfg.WORKER_CONCURRENCY}\n"
        )

    return run_replay(cfg, args.requests, args.workers, args.seed)


if __name__ == "__main__":
    sys.exit(main())
