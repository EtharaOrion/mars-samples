#!/bin/sh
set -e
mkdir -p /app/work /app/out
in=/app/work/parsed.txt
out=/app/work/stats.txt
sum=0
if [ -f "$in" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    n=$(printf '%s' "$line" | tr -d '[:space:]')
    case "$n" in ''|*[!0-9]*) continue;; esac
    sum=$((sum + n))
  done < "$in"
fi
printf '%s\n' "$sum" > "$out"
printf '%s\n' "stats" >> /app/out/order.log
