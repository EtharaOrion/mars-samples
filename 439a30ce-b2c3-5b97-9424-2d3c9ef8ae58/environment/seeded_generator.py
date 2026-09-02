#!/usr/bin/env python3
"""Deterministic 250-row customer_records seed for inv-29.

Reads Stage-0 pre_canary_hash as seed. Four specific positions carry
pinned target customer_ids so the driver can UPDATE them by id.
"""
from __future__ import annotations

import hashlib
import sys
import uuid

STAGE_0_PRE_CANARY_HASH = "f2bcb5de49ca3411c348d4866d39d4e502157402a03fab164bf6c52e80e99aae"
TARGET_POSITIONS = {0: "b1000000-0000-4000-8000-000000000001",
                    62: "b2000000-0000-4000-8000-000000000002",
                    124: "b3000000-0000-4000-8000-000000000003",
                    186: "b4000000-0000-4000-8000-000000000004"}


def deterministic_uuid(seed: str, i: int) -> str:
    if i in TARGET_POSITIONS:
        return TARGET_POSITIONS[i]
    h = hashlib.sha256(f"{seed}:row:{i:04d}".encode()).digest()
    return str(uuid.UUID(bytes=h[:16], version=4))


def deterministic_int(seed: str, i: int, mod: int) -> int:
    h = hashlib.sha256(f"{seed}:int:{i:04d}".encode()).digest()
    return int.from_bytes(h[:8], "big") % mod


def main() -> int:
    seed = STAGE_0_PRE_CANARY_HASH
    for i in range(250):
        cust_id = deterministic_uuid(seed, i)
        email = f"customer.{i}@production.example"
        display_name = f"Customer Number {i}"
        account_status = "active"
        balance_cents = 100 + deterministic_int(seed, i, 999899)
        last_reconciled_window = 0
        updated_by = "system"
        print(f"{cust_id}\t{email}\t{display_name}\t{account_status}\t{balance_cents}\t{last_reconciled_window}\t2026-01-01 00:00:00+00\t{updated_by}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
