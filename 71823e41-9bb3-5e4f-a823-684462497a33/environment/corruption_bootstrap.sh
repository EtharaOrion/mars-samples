#!/bin/bash
# FORGE inv-27 corruption bootstrap.
#
# Runs once at first-boot via entrypoint.sh, gated by
# /opt/holdout/.bootstrap_done. Steps:
#   1. Initialize the postgres cluster if the data dir is empty.
#   2. Start postgres directly (not via supervisord) on 127.0.0.1:5432.
#   3. seeded_generator.py bootstraps the app role + appdb database
#      and seeds the 5000-row catalog table. requests and audit stay
#      at 0 rows.
#   4. capture_baseline: compute catalog content hash and write
#      /opt/holdout/expected_catalog_content_hash.json and
#      /opt/holdout/expected_three_table_docs.json.
#   5. apply_corruption: sed -i in-place on /etc/pgbouncer/pgbouncer.ini
#      to change pool_mode=session -> transaction (P1) and
#      max_client_conn=100 -> 20 (P3); sed -i on /etc/app/config.py to
#      change CACHE_LOCK_TTL_SECONDS=30 -> 1 (P2).
#   6. verify_corruption: assert the three on-disk seed values.
#   7. Stop postgres; supervisord will restart it, along with pgbouncer
#      and redis, when entrypoint.sh execs supervisord.
set -euo pipefail

PG_BIN="/usr/lib/postgresql/16/bin"
PG_DATA="/var/lib/postgresql/16/main"
PG_LOG="/var/log/postgresql/postgresql-16-main.log"
PG_HBA="/etc/postgresql/16/main/pg_hba.conf"
PG_CONF="/etc/postgresql/16/main/postgresql.conf"
PGBOUNCER_INI="/etc/pgbouncer/pgbouncer.ini"
APP_CONFIG="/etc/app/config.py"
HOLDOUT="/opt/holdout"
LOG=/var/log/corruption_bootstrap.log

mkdir -p "$HOLDOUT" /var/log/postgresql
: > "$LOG"

log() {
    printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"
}

initdb_if_empty() {
    if [ -f "$PG_DATA/PG_VERSION" ]; then
        log "initdb_if_empty: cluster already initialized at $PG_DATA"
        return 0
    fi
    log "initdb_if_empty: initializing postgres cluster at $PG_DATA"
    mkdir -p "$PG_DATA" "$(dirname "$PG_HBA")"
    chown -R postgres:postgres "$PG_DATA" "$(dirname "$PG_HBA")"
    /usr/sbin/runuser -u postgres -- \
        "$PG_BIN/initdb" -D "$PG_DATA" --encoding=UTF8 --locale=C \
        --auth-local=trust --auth-host=trust --username=postgres \
        >>"$LOG" 2>&1

    cat > "$PG_HBA" <<'HBA_EOF'
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
HBA_EOF
    chown postgres:postgres "$PG_HBA"
    chmod 640 "$PG_HBA"

    cat > "$PG_CONF" <<'CONF_EOF'
listen_addresses = '127.0.0.1'
port = 5432
data_directory = '/var/lib/postgresql/16/main'
hba_file = '/etc/postgresql/16/main/pg_hba.conf'
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log/postgresql'
log_filename = 'postgresql-16-main.log'
log_file_mode = 0644
log_min_messages = warning
log_min_error_statement = error
log_line_prefix = '%m [%p] '
password_encryption = scram-sha-256
shared_buffers = 128MB
max_connections = 100
CONF_EOF
    chown postgres:postgres "$PG_CONF"
    chmod 644 "$PG_CONF"
}

start_pg() {
    log "start_pg: launching postgres as postgres user"
    /usr/sbin/runuser -u postgres -- \
        "$PG_BIN/pg_ctl" -D "$PG_DATA" -l "$PG_LOG" -w -t 60 start \
        >>"$LOG" 2>&1
    local i
    for i in $(seq 1 60); do
        if /usr/sbin/runuser -u postgres -- \
            "$PG_BIN/psql" -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc 'SELECT 1' \
            >/dev/null 2>&1; then
            log "start_pg: cluster responsive after ${i}s"
            return 0
        fi
        sleep 1
    done
    log "start_pg: cluster never became responsive"
    tail -80 "$PG_LOG" || true
    return 1
}

stop_pg() {
    log "stop_pg: draining postgres"
    /usr/sbin/runuser -u postgres -- \
        "$PG_BIN/pg_ctl" -D "$PG_DATA" -m fast -w -t 45 stop \
        >>"$LOG" 2>&1 || true
    sleep 2
}

seed_data() {
    log "seed_data: bootstrapping role/db and seeding catalog"
    python3 /opt/holdout/seeded_generator.py all >>"$LOG" 2>&1
}

capture_baseline() {
    log "capture_baseline: computing catalog content hash"
    python3 <<'PY' > "$HOLDOUT/expected_catalog_content_hash.json.tmp"
import hashlib
import json
import subprocess

result = subprocess.run(
    [
        "psql", "-h", "127.0.0.1", "-p", "5432", "-U", "postgres",
        "-d", "appdb", "-tAc",
        "SELECT catalog_id, sku, description, price, "
        "array_to_string(tags, ',') FROM catalog ORDER BY catalog_id",
    ],
    check=True, capture_output=True,
)
digest = hashlib.sha256(result.stdout).hexdigest()
print(json.dumps({"catalog_content_hash": digest,
                  "catalog_row_bytes": len(result.stdout)},
                 sort_keys=True, separators=(",", ":"), ensure_ascii=True))
PY
    mv "$HOLDOUT/expected_catalog_content_hash.json.tmp" \
       "$HOLDOUT/expected_catalog_content_hash.json"
    log "capture_baseline: wrote $HOLDOUT/expected_catalog_content_hash.json"

    cat > "$HOLDOUT/expected_three_table_docs.json.tmp" <<'JSON'
{"audit":{"post_replay":1000,"start":0},"catalog":{"post_replay":5000,"start":5000},"requests":{"post_replay":1000,"start":0}}
JSON
    mv "$HOLDOUT/expected_three_table_docs.json.tmp" \
       "$HOLDOUT/expected_three_table_docs.json"
    log "capture_baseline: wrote $HOLDOUT/expected_three_table_docs.json"
}

apply_corruption() {
    log "apply_corruption: applying P1/P2/P3 to on-disk configs"

    sed -i -E 's/^pool_mode[[:space:]]*=[[:space:]]*session/pool_mode = transaction/' "$PGBOUNCER_INI"
    log "apply_corruption: P1 pool_mode=transaction seeded in $PGBOUNCER_INI"

    sed -i -E 's/^max_client_conn[[:space:]]*=[[:space:]]*100/max_client_conn = 20/' "$PGBOUNCER_INI"
    log "apply_corruption: P3 max_client_conn=20 seeded in $PGBOUNCER_INI"

    sed -i -E 's/^CACHE_LOCK_TTL_SECONDS[[:space:]]*=[[:space:]]*30/CACHE_LOCK_TTL_SECONDS = 1/' "$APP_CONFIG"
    log "apply_corruption: P2 CACHE_LOCK_TTL_SECONDS=1 seeded in $APP_CONFIG"
}

verify_corruption() {
    log "verify_corruption: asserting P1/P2/P3 on the on-disk configs"

    if ! grep -qE '^pool_mode[[:space:]]*=[[:space:]]*transaction' "$PGBOUNCER_INI"; then
        log "verify_corruption: P1 not applied (pool_mode)"
        grep -E '^pool_mode' "$PGBOUNCER_INI" >>"$LOG" || true
        return 1
    fi
    log "verify_corruption: P1 pool_mode=transaction confirmed"

    if ! grep -qE '^max_client_conn[[:space:]]*=[[:space:]]*20' "$PGBOUNCER_INI"; then
        log "verify_corruption: P3 not applied (max_client_conn)"
        grep -E '^max_client_conn' "$PGBOUNCER_INI" >>"$LOG" || true
        return 1
    fi
    log "verify_corruption: P3 max_client_conn=20 confirmed"

    if ! grep -qE '^CACHE_LOCK_TTL_SECONDS[[:space:]]*=[[:space:]]*1[[:space:]]*$' "$APP_CONFIG"; then
        log "verify_corruption: P2 not applied (CACHE_LOCK_TTL_SECONDS)"
        grep -E '^CACHE_LOCK_TTL_SECONDS' "$APP_CONFIG" >>"$LOG" || true
        return 1
    fi
    log "verify_corruption: P2 CACHE_LOCK_TTL_SECONDS=1 confirmed"
}

main_bootstrap() {
    log "main_bootstrap: begin"
    chown -R postgres:postgres /var/log/postgresql

    initdb_if_empty
    start_pg
    seed_data
    capture_baseline
    apply_corruption
    verify_corruption
    stop_pg

    log "main_bootstrap: complete"
}

case "${1:-}" in
    bootstrap) main_bootstrap ;;
    *) echo "usage: $0 bootstrap" >&2; exit 2 ;;
esac
