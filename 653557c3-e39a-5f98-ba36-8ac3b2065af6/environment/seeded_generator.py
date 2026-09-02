#!/usr/bin/env python3
# Deterministic seeded generator for the 250-row customer_records table.
import hashlib
import psycopg2
import uuid

SEED = 30
ROW_COUNT = 250
NAMES = [f"Customer {i:03d}" for i in range(ROW_COUNT)]


def deterministic_uuid(i: int) -> str:
    h = hashlib.sha256(f"inv-30-customer-{i:04d}-seed-{SEED}".encode()).digest()
    return str(uuid.UUID(bytes=h[:16], version=4))


def deterministic_balance(i: int) -> int:
    return 10000 + (hashlib.sha256(f"balance-{i}-seed-{SEED}".encode()).digest()[0] * 3907) % 990000


def main() -> None:
    conn = psycopg2.connect(dbname="production", user="postgres", host="")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE customer_records;")
        rows = [
            (deterministic_uuid(i), f"customer{i:03d}@example.internal", NAMES[i],
             "active", deterministic_balance(i), "2026-08-12T00:00:00+00:00")
            for i in range(ROW_COUNT)
        ]
        cur.executemany(
            "INSERT INTO customer_records (customer_id, email, display_name, account_status, balance_cents, updated_at)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            rows,
        )
    conn.close()


if __name__ == "__main__":
    main()
