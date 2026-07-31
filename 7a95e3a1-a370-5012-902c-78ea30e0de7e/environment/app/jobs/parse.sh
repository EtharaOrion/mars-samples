#!/bin/sh
set -e
mkdir -p /app/work /app/out
in=/app/inputs/raw.txt
out=/app/work/parsed.txt
: > "$out"
if [ -f "$in" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    n=$(printf '%s' "$line" | tr -d '[:space:]')
    case "$n" in ''|*[!0-9]*) continue;; esac
    if [ "$n" -ge 7 ]; then printf '%s\n' "$n" >> "$out"; fi
  done < "$in"
fi
printf '%s\n' "parse" >> /app/out/order.log
