# Postgres corrupt WAL selective recovery

You have a single-container postgres 16 service in a failed-to-start state.
Bring the cluster back to a servable state that preserves the strictly larger
post-checkpoint committed row set, and author two files under `/workspace/`
that together carry the recovery: `/workspace/recover.sh` (executable) and
`/workspace/notes.md`.

## What is broken
- The last write-ahead-log segment under `/var/lib/postgresql/data/pg_wal/`
  is truncated at a non-record boundary.
- `pg_control` still references an LSN inside the truncated segment.
- A stale `postmaster.pid` remains from an ungraceful shutdown.
- A background loop rotates `pg_hba.conf` between trust and scram-sha-256
  every 90 seconds while your recovery runs.

## What is intact
- `/var/lib/postgresql/data/` (except for the torn WAL tail and the stale
  pid file).
- Three business tables (`accounts`, `ledger_entries`, `audit_events`) with
  a foreign-key edge from `ledger_entries` to `accounts` and another from
  `audit_events` to `ledger_entries`, and btree primary keys on all three.
- The `amcheck` extension is available.
- `/workspace/input/pg_wal_snapshot/` (inspection copy of pg_wal).
- `/workspace/input/basebackup/last_good.sql` (checkpoint-boundary dump,
  strictly missing every post-checkpoint transaction).
- `/workspace/input/reference/pg_control_readout.txt` (pre-crash
  pg_controldata output).

## What you author
- `/workspace/recover.sh`  -- executable; exit 0 on success.  When invoked as
  `bash /workspace/recover.sh` from `/workspace/` with `LC_ALL=C` and the
  pinned toolchain on `PATH`, it MUST complete recovery end-to-end without
  external network and leave the postmaster ready on the unix socket at
  `/var/run/postgresql`.
- `/workspace/notes.md`  -- summarize the recovery route, name the observed
  last-checkpoint LSN, name the pg_waldump-derived safe replay ceiling LSN,
  and explain why each table holds strictly more rows than the pre-checkpoint
  dump would restore.

Read `/workspace/README_FOR_AGENT.md` for the full file inventory, red-line
list, and shortcut-guard rationale.  Grading is entirely container-local: the
verifier will invoke `recover.sh`, poll `pg_isready`, run an 8-probe SQL
matrix over the unix socket, and apply six deliverable checks D1-D6.
