#!/usr/bin/env python3
"""FORGE inv-27 seeded generator.

Creates the three pre-existing tables in the `appdb` database
(`requests`, `catalog`, `audit`), seeds `catalog` with a deterministic
5000-row stream, and leaves `requests`/`audit` empty at 0 rows.

Determinism: SEED_HEX drives a single random.Random keyed by row
index, so per-row content is bit-identical across authoring hosts.
Every serialization is canonical: catalog_id as lowercase UUID
string, sku/description as ASCII strings, price as Decimal with
two-place canonical form via str(Decimal), tags as a Python list of
lowercase ASCII slug strings inserted via psycopg2 array binding.
No float fields exist anywhere in the schema.

The SEED_HEX constant is authored at Stage 2 and pinned into the
bundle bytes. Pre-canary hash is independent of this pin because
the hash is computed over canary-stripped bytes and this constant
is not a canary.
"""
from __future__ import annotations

import argparse
import decimal
import hashlib
import random
import subprocess
import sys
import time
import uuid

import psycopg2


PG_HOST = "127.0.0.1"
PG_PORT = 5432
PG_DB = "appdb"
PG_USER = "app"
PG_PASSWORD = "app-password"
PG_ADMIN_USER = "postgres"

SEED_HEX = "5f4e3d2c1b0a99887766554433221100ffeeddccbbaa998877665544332211aa"

CATALOG_ROWS = 5000

CANONICAL_TAG_POOL = (
    "alpha", "bravo", "charlie", "delta",
    "echo", "foxtrot", "golf", "hotel",
    "india", "juliet", "kilo", "lima",
    "mike", "november", "oscar", "papa",
)

CREATE_TABLES_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS requests (
    request_id uuid PRIMARY KEY,
    worker_id integer NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS catalog (
    catalog_id uuid PRIMARY KEY,
    sku text NOT NULL,
    description text NOT NULL,
    price numeric NOT NULL,
    tags text[] NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS audit (
    audit_id bigserial PRIMARY KEY,
    worker_id integer NOT NULL,
    request_id uuid NOT NULL,
    note text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
"""

INSERT_CATALOG_SQL = (
    "INSERT INTO catalog (catalog_id, sku, description, price, tags, updated_at) "
    "VALUES (%s, %s, %s, %s, %s, %s::timestamptz)"
)

FIXED_UPDATED_AT = "2026-01-01T00:00:00+00:00"


def row_seed(index: int) -> random.Random:
    digest = hashlib.sha256((SEED_HEX + ":" + str(index)).encode("ascii")).hexdigest()
    return random.Random(int(digest[:16], 16))


def deterministic_uuid(index: int) -> uuid.UUID:
    material = hashlib.sha256(
        (SEED_HEX + ":catalog:" + str(index)).encode("ascii")
    ).digest()
    return uuid.UUID(bytes=material[:16], version=5)


def make_catalog_row(index: int) -> tuple:
    rng = row_seed(index)
    cid = deterministic_uuid(index)
    sku = f"SKU-{index:06d}"
    description = f"catalog-item-{index:06d}-{hashlib.sha256(str(index).encode()).hexdigest()[:16]}"
    price_cents = rng.randrange(100, 100000)
    price = decimal.Decimal(price_cents) / decimal.Decimal(100)
    price = price.quantize(decimal.Decimal("0.01"))
    tag_count = 1 + rng.randrange(4)
    tags = sorted(rng.sample(CANONICAL_TAG_POOL, tag_count))
    return (str(cid), sku, description, str(price), tags, FIXED_UPDATED_AT)


def wait_for_postgres(deadline_s: int = 180) -> None:
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        try:
            conn = psycopg2.connect(
                host=PG_HOST, port=PG_PORT, dbname="postgres",
                user=PG_ADMIN_USER, connect_timeout=5,
            )
            conn.close()
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise SystemExit("postgres did not become reachable within %d s" % deadline_s)


def bootstrap_role_and_database() -> None:
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname="postgres",
        user=PG_ADMIN_USER, connect_timeout=15,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (PG_USER,))
            if cur.fetchone() is None:
                cur.execute(
                    f"CREATE ROLE {PG_USER} LOGIN PASSWORD %s",
                    (PG_PASSWORD,),
                )
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (PG_DB,))
            if cur.fetchone() is None:
                cur.execute(f"CREATE DATABASE {PG_DB} OWNER {PG_USER}")
    finally:
        conn.close()


def create_tables_and_seed_catalog() -> None:
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB,
        user=PG_ADMIN_USER, connect_timeout=15,
    )
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLES_SQL)
            cur.execute(f"GRANT ALL ON SCHEMA public TO {PG_USER}")
            cur.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA public TO {PG_USER}")
            cur.execute(f"GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {PG_USER}")

            cur.execute("SELECT count(*) FROM catalog")
            existing = cur.fetchone()[0]
            if existing == CATALOG_ROWS:
                conn.commit()
                return
            if existing != 0:
                raise SystemExit(f"catalog table has {existing} rows, expected 0 or {CATALOG_ROWS}")

            for i in range(1, CATALOG_ROWS + 1):
                cur.execute(INSERT_CATALOG_SQL, make_catalog_row(i))
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="FORGE inv-27 seeded generator")
    ap.add_argument("phase", nargs="?", default="all",
                    choices=("all", "bootstrap", "seed"),
                    help="phase to run (default: all)")
    args = ap.parse_args()

    wait_for_postgres()

    if args.phase in ("all", "bootstrap"):
        bootstrap_role_and_database()

    if args.phase in ("all", "seed"):
        create_tables_and_seed_catalog()

    print(f"seeded_generator: phase={args.phase} complete "
          f"(catalog target={CATALOG_ROWS})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
