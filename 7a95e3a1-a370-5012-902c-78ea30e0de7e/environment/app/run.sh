#!/bin/sh
set -e
cd /app
rm -rf /app/work /app/out
mkdir -p /app/work /app/out
while IFS= read -r job || [ -n "$job" ]; do
  job=$(printf '%s' "$job" | tr -d '[:space:]')
  [ -z "$job" ] && continue
  sh /app/jobs/"$job".sh
done < /app/schedule.txt
