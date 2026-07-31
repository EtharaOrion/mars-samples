#!/bin/sh
set -e
mkdir -p /app/work /app/out
sfile=/app/work/stats.txt
wfile=/app/work/weighted.txt
bfile=/app/inputs/base.txt
out=/app/work/merged.txt
readint() { f="$1"; v=0; if [ -s "$f" ]; then v=$(tr -d '[:space:]' < "$f"); fi; case "$v" in ''|*[!0-9]*) v=0;; esac; printf '%s' "$v"; }
s=$(readint "$sfile")
w=$(readint "$wfile")
b=$(readint "$bfile")
r=$((s + w + b))
{ printf 'stats_sum=%s\n' "$s"; printf 'weighted=%s\n' "$w"; printf 'base=%s\n' "$b"; printf 'result=%s\n' "$r"; } > "$out"
printf '%s\n' "merge" >> /app/out/order.log
