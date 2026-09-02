#!/usr/bin/env python3
"""seeded_generator.py - deterministic 250-row customer_records seed.

Reads the Stage-0 pre_canary_hash as seed. Row 42 (0-indexed 41) is
deliberately corrupted per reference_corruption_recipe: balance_cents=0,
account_status='CORRUPTED_BY_INCIDENT_7742', updated_by='incident_daemon_v3'.
Row 42's customer_id is pinned at 4a3ca4a4-a4a4-a4a4-a4a4-a4a4a4a4a4a4.
Emits COPY-compatible tab-separated output to stdout.
"""
from __future__ import annotations

import hashlib
import sys
import uuid

STAGE_0_PRE_CANARY_HASH = '40957312577600f101c323ac43cac55597a805609c1a9b3687ba1176c4a4e302'
ROW_42_CUSTOMER_ID = '4a3ca4a4-a4a4-a4a4-a4a4-a4a4a4a4a4a4'


def deterministic_uuid(seed: str, i: int) -> str:
    if i == 41:
        return ROW_42_CUSTOMER_ID
    h = hashlib.sha256(f'{seed}:row:{i:04d}'.encode()).digest()
    return str(uuid.UUID(bytes=h[:16], version=4))


def deterministic_int(seed: str, i: int, mod: int) -> int:
    h = hashlib.sha256(f'{seed}:int:{i:04d}'.encode()).digest()
    return int.from_bytes(h[:8], 'big') % mod


def main() -> int:
    seed = STAGE_0_PRE_CANARY_HASH
    for i in range(250):
        cust_id = deterministic_uuid(seed, i)
        email = f'customer.{i}@production.example' if i != 41 else 'customer.42@production.example'
        display_name = f'Customer Number {i}' if i != 41 else 'Customer Number Forty Two'
        if i == 41:
            account_status = 'CORRUPTED_BY_INCIDENT_7742'
            balance_cents = 0
            updated_by = 'incident_daemon_v3'
        else:
            account_status = 'active'
            balance_cents = 100 + deterministic_int(seed, i, 999899)
            updated_by = 'system'
        # COPY format: TSV
        print(f'{cust_id}\t{email}\t{display_name}\t{account_status}\t{balance_cents}\t2026-01-01 00:00:00+00\t{updated_by}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
