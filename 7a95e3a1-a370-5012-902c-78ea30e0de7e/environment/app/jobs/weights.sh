#!/bin/sh
set -e
mkdir -p /app/work /app/out
pin=/app/work/parsed.txt
win=/app/inputs/weights.txt
out=/app/work/weighted.txt
count=0
if [ -f "$pin" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    n=$(printf '%s' "$line" | tr -d '[:space:]')
    case "$n" in ''|*[!0-9]*) continue;; esac
    count=$((count + 1))
  done < "$pin"
fi
w=0
if [ -s "$win" ]; then
  w=$(tr -d '[:space:]' < "$win")
  case "$w" in ''|*[!0-9]*) w=0;; esac
fi
printf '%s\n' "$((count * w))" > "$out"
printf '%s\n' "weights" >> /app/out/order.log
