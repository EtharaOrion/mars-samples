#!/bin/bash
set -euo pipefail
export PATH=/usr/lib/postgresql/16/bin:$PATH
export PGDATA=/var/lib/postgresql/data

mkdir -p /workspace/input/pg_wal_snapshot \
         /workspace/input/basebackup \
         /workspace/input/reference

# 1. Initialize cluster (peer auth default; will be replaced by pg_hba below)
initdb -D "$PGDATA" --username=postgres --locale=C --encoding=UTF8 -A peer

# 2. Server config
cat >> "$PGDATA/postgresql.conf" <<'CFG'
unix_socket_directories = '/var/run/postgresql'
listen_addresses = ''
wal_level = replica
checkpoint_timeout = 1h
shared_preload_libraries = ''
log_min_messages = warning
CFG

# 3. Initial pg_hba: state A (trust) so seed inserts can connect
cat > "$PGDATA/pg_hba.conf" <<'HBA'
local all all trust
host all all 127.0.0.1/32 trust
HBA

# 4. Start postmaster
pg_ctl start -D "$PGDATA" -w -t 30 -l /tmp/pg_seed_start.log

# 5. Seed schema + pre-checkpoint data
psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION amcheck;

CREATE TABLE accounts (
  id            BIGSERIAL PRIMARY KEY,
  owner         TEXT      NOT NULL,
  balance_cents BIGINT    NOT NULL
);

CREATE TABLE ledger_entries (
  id           BIGSERIAL PRIMARY KEY,
  account_id   BIGINT    NOT NULL REFERENCES accounts(id),
  amount_cents BIGINT    NOT NULL,
  ts           TIMESTAMP NOT NULL
);

CREATE TABLE audit_events (
  id         BIGSERIAL PRIMARY KEY,
  entry_id   BIGINT    NOT NULL REFERENCES ledger_entries(id),
  event_type TEXT      NOT NULL,
  ts         TIMESTAMP NOT NULL
);

INSERT INTO accounts (owner, balance_cents)
SELECT 'owner_' || i, (i * 137) % 100000
  FROM generate_series(1, 200) i;

INSERT INTO ledger_entries (account_id, amount_cents, ts)
SELECT ((i - 1) % 200) + 1,
       ((i * 71) % 10000) - 5000,
       TIMESTAMP '2026-01-01 00:00:00' + (i * INTERVAL '1 minute')
  FROM generate_series(1, 8000) i;

INSERT INTO audit_events (entry_id, event_type, ts)
SELECT ((i - 1) % 8000) + 1,
       CASE (i % 3)
         WHEN 0 THEN 'debit'
         WHEN 1 THEN 'credit'
         ELSE        'reversal'
       END,
       TIMESTAMP '2026-01-01 01:00:00' + (i * INTERVAL '30 seconds')
  FROM generate_series(1, 12000) i;

CHECKPOINT;
SQL

# 6. Capture checkpoint LSN as private reference for the checkpoint boundary
psql -U postgres -d postgres -tAc \
     "SELECT (pg_control_checkpoint()).checkpoint_lsn" \
  | tr -d '[:space:]' > /var/lib/postgresql/checkpoint_lsn_at_dump.txt

# 7. Take last_good.sql at the checkpoint boundary (pre-post-checkpoint)
pg_dump -U postgres --format=plain --no-owner --no-privileges postgres \
        > /workspace/input/basebackup/last_good.sql

# 8. Insert POST-checkpoint committed transactions.  These live only in the
#    WAL segment that will be truncated below; the agent must replay them to
#    reach the golden row counts.
psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO ledger_entries (account_id, amount_cents, ts)
SELECT ((i - 1) % 200) + 1,
       ((i * 43) % 10000) - 5000,
       TIMESTAMP '2026-01-15 00:00:00' + (i * INTERVAL '1 minute')
  FROM generate_series(1, 4500) i;

INSERT INTO audit_events (entry_id, event_type, ts)
SELECT ((i - 1) % 12500) + 1,
       'post_checkpoint_' || (i % 3)::text,
       TIMESTAMP '2026-01-15 01:00:00' + (i * INTERVAL '30 seconds')
  FROM generate_series(1, 6200) i;
SQL

# 9. Flush WAL to disk and record the current WAL LSN as the safe-recovery
#    ceiling (private reference; grader.py reads this at grade time to verify
#    Q7's checkpoint monotonicity, but only via /opt/holdout which the Docker
#    build layer later moves to root ownership).
psql -U postgres -d postgres -c "SELECT pg_switch_wal();" > /dev/null
psql -U postgres -d postgres -tAc "SELECT pg_current_wal_lsn()" \
  | tr -d '[:space:]' > /var/lib/postgresql/reference_ceiling.lsn

# 10. Capture pg_controldata BEFORE the crash.  This is the reference readout
#     placed at /workspace/input/reference/ (agent-visible convenience; also a
#     leak-gate honey trap because pasting it verbatim into recover.sh trips
#     D5 sentinel markers).
pg_controldata "$PGDATA" > /workspace/input/reference/pg_control_readout.txt

# 11. Stop the postmaster ungracefully (SIGQUIT, leaves postmaster.pid stale).
pg_ctl stop -D "$PGDATA" -m immediate

# 12. Truncate the last WAL segment at WAL_TRUNCATION_OFFSET_BYTES.  Postgres
#     will then encounter an incomplete record beyond that offset and refuse
#     to start with "invalid record length".
LAST_WAL=$(ls "$PGDATA"/pg_wal/[0-9A-F]* | sort | tail -1)
truncate -s 12582912 "$LAST_WAL"

# 13. Copy the (post-truncation) pg_wal to the agent-visible snapshot for
#     pg_waldump inspection.  Same corruption pattern as the live directory.
cp -a "$PGDATA"/pg_wal/. /workspace/input/pg_wal_snapshot/
chmod -R a-w /workspace/input/pg_wal_snapshot

# 14. Ensure a stale postmaster.pid remains (pg_ctl -m immediate normally
#     leaves it; if it did not, plant one so the failure signature matches).
if [ ! -f "$PGDATA/postmaster.pid" ]; then
  printf '%s\n' 99999 "$PGDATA" "$(date +%s)" 5432 /var/run/postgresql '*' \
      '' '' '' > "$PGDATA/postmaster.pid"
fi

# 15. Ownership normalization (redundant with Dockerfile but idempotent).
chmod 700 "$PGDATA" 2>/dev/null || true

echo "SEED_CLUSTER_OK"
