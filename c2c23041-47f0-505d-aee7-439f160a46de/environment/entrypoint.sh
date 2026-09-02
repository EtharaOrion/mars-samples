#!/usr/bin/env bash
set -euo pipefail

mkdir -p /var/log/nginx /var/log/upstream

nohup python3 /opt/upstream/upstream_server.py \
    > /var/log/upstream/upstream.log 2>&1 &

for _ in 1 2 3 4 5 6 7 8 9 10; do
    if ss -ltn "sport = :8080" | grep -q ":8080"; then
        break
    fi
    sleep 0.2
done

exec sleep infinity
