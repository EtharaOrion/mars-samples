#!/bin/bash
# FORGE inv-26 corruption bootstrap.
#
# Runs once at first-boot via entrypoint.sh, gated by
# /opt/holdout/.bootstrap_done. Steps:
#   1. Start ES; seed orders-2026-{06,07,08} only.
#   2. Apply P2 (per-index rack=rack-b on all three orders indices).
#      P2 is applied here, before the state snapshot, so its per-index
#      metadata is captured in the snapshot and survives the P3 restore.
#   3. Stop ES; snapshot /var/lib/elasticsearch/_state/ to
#      /tmp/state_backup_pre_analytics (has orders + P2; no analytics).
#   4. Start ES; seed analytics-2026-05.
#   5. capture_baseline: hash all four indices while analytics is
#      present in cluster state (baseline must include analytics).
#   6. Apply P3: enumerate the analytics UUID, stop ES, RESTORE the
#      pre-analytics _state/ snapshot. Analytics disappears from
#      cluster state but its shard files stay on disk under
#      /var/lib/elasticsearch/indices/UUID/. This is the ES 8.x-safe
#      dangling-index recipe (no DELETE, so no tombstone GC).
#   7. Start ES; apply P1 (persistent
#      cluster.routing.allocation.enable=none). P1 is applied AFTER
#      the state restore so it is not wiped away.
#   8. verify_corruption: assert P1 persistent, P2 per-index on all
#      three orders indices, and analytics-2026-05 surfaced under
#      GET /_dangling. Stop ES.
#   9. Exit; supervisord runs ES normally, agent sees corrupted state.
set -euo pipefail

ES_BASE="http://127.0.0.1:9200"
ES_BIN="/usr/share/elasticsearch/bin/elasticsearch"
ES_PID_FILE="/tmp/es_bootstrap.pid"
ES_DATA="/var/lib/elasticsearch"
STATE_BACKUP="/tmp/state_backup_pre_analytics"
HOLDOUT="/opt/holdout"
LOG=/var/log/es_bootstrap.log

mkdir -p "$HOLDOUT"
: > "$LOG"

log() {
    printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"
}

start_es() {
    log "start_es: launching elasticsearch as elasticsearch user"
    rm -f "$ES_PID_FILE"
    /usr/sbin/runuser -u elasticsearch -- \
        env ES_JAVA_OPTS="-Xms512m -Xmx512m" \
            ES_PATH_CONF=/etc/elasticsearch \
            ES_JAVA_HOME="/usr/lib/jvm/java-17-openjdk-$(dpkg --print-architecture)" \
        "$ES_BIN" -p "$ES_PID_FILE" >>"$LOG" 2>&1 &
    local i
    for i in $(seq 1 300); do
        if [ -f "$ES_PID_FILE" ]; then
            log "start_es: pid file present after ${i}s"
            break
        fi
        sleep 1
    done
    if [ ! -f "$ES_PID_FILE" ]; then
        log "start_es: pid file never appeared"
        log "start_es: dumping ES log tail for diagnostics"
        tail -80 "$LOG" || true
        echo "---jvm-arch-diag---"
        echo "dpkg-arch: $(dpkg --print-architecture 2>&1)"
        echo "expected-java: /usr/lib/jvm/java-17-openjdk-$(dpkg --print-architecture)"
        ls -la /usr/lib/jvm/ 2>&1 || true
        return 1
    fi
    for i in $(seq 1 180); do
        if curl -sf "$ES_BASE/_cluster/health?wait_for_status=red&timeout=5s" \
                >/dev/null 2>&1; then
            log "start_es: cluster responsive after ${i}s"
            return 0
        fi
        sleep 2
    done
    log "start_es: cluster never became responsive"
    return 1
}

stop_es() {
    log "stop_es: draining elasticsearch"
    if [ -f "$ES_PID_FILE" ]; then
        local pid
        pid=$(cat "$ES_PID_FILE")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
            local i
            for i in $(seq 1 60); do
                if ! kill -0 "$pid" 2>/dev/null; then
                    log "stop_es: exited after ${i}s"
                    break
                fi
                sleep 1
            done
            if kill -0 "$pid" 2>/dev/null; then
                log "stop_es: TERM did not close after 60s, escalating"
                kill -KILL "$pid" 2>/dev/null || true
                sleep 3
            fi
        fi
    fi
    for i in $(seq 1 30); do
        if ! curl -sf "$ES_BASE/_cluster/health" >/dev/null 2>&1; then
            log "stop_es: REST port closed after ${i}s"
            break
        fi
        sleep 1
    done
    rm -f "$ES_PID_FILE"
    sleep 3
}

capture_baseline() {
    log "capture_baseline: computing per-index SHA-256 content hashes"
    python3 <<'PY' > "$HOLDOUT/expected_four_index_content_hash.json.tmp"
import hashlib
import json
import urllib.request

INDICES = ("orders-2026-06", "orders-2026-07", "orders-2026-08", "analytics-2026-05")
ES = "http://127.0.0.1:9200"

def fetch_all(name):
    url = ES + "/" + name + "/_search"
    body = json.dumps({
        "size": 10000,
        "sort": [{"_doc": {"order": "asc"}}],
        "_source": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read())
    return payload

result = {}
for name in INDICES:
    payload = fetch_all(name)
    hits = payload["hits"]["hits"]
    total = payload["hits"]["total"]["value"]
    docs = []
    for hit in hits:
        src = json.dumps(hit["_source"], sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        docs.append(hit["_id"] + ":" + src)
    docs.sort(key=lambda s: s.split(":", 1)[0])
    payload_str = "\n".join(docs)
    h = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
    result[name] = {"docs": total, "content_hash_sha256": h}

print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
PY
    mv "$HOLDOUT/expected_four_index_content_hash.json.tmp" \
       "$HOLDOUT/expected_four_index_content_hash.json"
    log "capture_baseline: wrote $HOLDOUT/expected_four_index_content_hash.json"

    python3 <<'PY' > "$HOLDOUT/expected_four_index_docs.json.tmp"
import json
result = {
    "orders-2026-06":    {"docs": 2500, "primary_shards": 3, "replicas": 0},
    "orders-2026-07":    {"docs": 2700, "primary_shards": 3, "replicas": 0},
    "orders-2026-08":    {"docs": 2400, "primary_shards": 3, "replicas": 0},
    "analytics-2026-05": {"docs": 900,  "primary_shards": 1, "replicas": 0},
}
print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
PY
    mv "$HOLDOUT/expected_four_index_docs.json.tmp" \
       "$HOLDOUT/expected_four_index_docs.json"
    log "capture_baseline: wrote $HOLDOUT/expected_four_index_docs.json"
}

apply_p1() {
    log "apply_p1: setting persistent cluster.routing.allocation.enable=none"
    curl -sfS -X PUT "$ES_BASE/_cluster/settings" \
        -H 'Content-Type: application/json' \
        -d '{"persistent": {"cluster.routing.allocation.enable": "none"}}' \
        >>"$LOG"
    echo >> "$LOG"
}

apply_p2() {
    log "apply_p2: setting per-index routing.allocation.require.rack=rack-b on three orders indices"
    for idx in orders-2026-06 orders-2026-07 orders-2026-08; do
        curl -sfS -X PUT "$ES_BASE/$idx/_settings" \
            -H 'Content-Type: application/json' \
            -d '{"index.routing.allocation.require.rack": "rack-b"}' \
            >>"$LOG"
        echo >> "$LOG"
    done
}

snapshot_state_pre_analytics() {
    log "snapshot_state_pre_analytics: stopping ES to snapshot _state/"
    stop_es
    rm -rf "$STATE_BACKUP"
    cp -a "$ES_DATA/_state" "$STATE_BACKUP"
    sync
    log "snapshot_state_pre_analytics: backed up $(ls -1 "$STATE_BACKUP" | wc -l | tr -d ' ') files to $STATE_BACKUP"
}

apply_p3() {
    log "apply_p3: making analytics-2026-05 dangling via ES 8.x-safe state-file surgery"
    local uuid
    uuid=$(curl -sfS "$ES_BASE/_cat/indices/analytics-2026-05?h=uuid&format=json" \
        | python3 -c 'import json,sys;d=json.loads(sys.stdin.read());print(d[0]["uuid"])')
    if [ -z "$uuid" ] || [ "$uuid" = "null" ]; then
        log "apply_p3: could not enumerate analytics-2026-05 uuid"
        return 1
    fi
    log "apply_p3: analytics-2026-05 uuid = $uuid"
    printf '%s\n' "$uuid" > "$HOLDOUT/analytics_dangling_uuid.txt"

    curl -sfS -X POST "$ES_BASE/_flush?wait_if_ongoing=true" >>"$LOG"
    echo >> "$LOG"

    if [ ! -d "$STATE_BACKUP" ]; then
        log "apply_p3: FATAL — $STATE_BACKUP missing (snapshot_state_pre_analytics must run before apply_p3)"
        return 1
    fi
    if [ ! -d "$ES_DATA/indices/$uuid" ]; then
        log "apply_p3: FATAL — analytics shard dir $ES_DATA/indices/$uuid missing before restore"
        ls -la "$ES_DATA/indices" >>"$LOG" || true
        return 1
    fi

    stop_es

    rm -rf "$ES_DATA/_state"
    cp -a "$STATE_BACKUP" "$ES_DATA/_state"
    chown -R elasticsearch:elasticsearch "$ES_DATA/_state"
    sync
    log "apply_p3: restored pre-analytics _state/ ($(ls -1 "$ES_DATA/_state" | wc -l | tr -d ' ') files); analytics shard dir preserved on disk"
    rm -rf "$STATE_BACKUP"
}

verify_corruption() {
    log "verify_corruption: asserting P1/P2/P3 on the live cluster"

    local enable
    enable=$(curl -sfS "$ES_BASE/_cluster/settings?flat_settings=true" \
        | python3 -c 'import json,sys;d=json.loads(sys.stdin.read());print(d.get("persistent",{}).get("cluster.routing.allocation.enable",""))')
    if [ "$enable" != "none" ]; then
        log "verify_corruption: P1 not persisted (enable=$enable)"
        return 1
    fi
    log "verify_corruption: P1 persisted (enable=$enable)"

    for idx in orders-2026-06 orders-2026-07 orders-2026-08; do
        local rack
        rack=$(curl -sfS "$ES_BASE/$idx/_settings" \
            | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
name = list(d.keys())[0]
print(d[name]['settings']['index'].get('routing',{}).get('allocation',{}).get('require',{}).get('rack',''))")
        if [ "$rack" != "rack-b" ]; then
            log "verify_corruption: P2 not applied on $idx (rack=$rack)"
            return 1
        fi
        log "verify_corruption: P2 applied on $idx (rack=$rack)"
    done

    local dangling_uuid=""
    local j
    for j in $(seq 1 30); do
        dangling_uuid=$(curl -sfS "$ES_BASE/_dangling" \
            | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
for e in d.get('dangling_indices', []):
    if e.get('index_name') == 'analytics-2026-05':
        print(e['index_uuid'])
        break")
        if [ -n "$dangling_uuid" ]; then
            log "verify_corruption: P3 dangling detected after ~$((j*2))s"
            break
        fi
        sleep 2
    done
    if [ -z "$dangling_uuid" ]; then
        log "verify_corruption: P3 did not surface analytics-2026-05 as dangling after 60s"
        curl -sfS "$ES_BASE/_dangling" | tee -a "$LOG" >/dev/null
        return 1
    fi
    log "verify_corruption: P3 dangling analytics-2026-05 uuid=$dangling_uuid"

    stop_es
}

main_bootstrap() {
    log "main_bootstrap: begin (Cycle 10 P3 protocol: state-snapshot restore)"
    chown -R elasticsearch:elasticsearch "$ES_DATA" /var/log/elasticsearch

    start_es
    /opt/holdout/seeded_generator.py orders
    apply_p2
    snapshot_state_pre_analytics

    start_es
    /opt/holdout/seeded_generator.py analytics
    capture_baseline
    apply_p3

    start_es
    apply_p1
    verify_corruption

    log "main_bootstrap: complete"
}

case "${1:-}" in
    bootstrap) main_bootstrap ;;
    *) echo "usage: $0 bootstrap" >&2; exit 2 ;;
esac
