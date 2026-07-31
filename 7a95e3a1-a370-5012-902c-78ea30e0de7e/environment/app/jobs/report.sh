#!/bin/sh
set -e
mkdir -p /app/work /app/out
in=/app/work/merged.txt
out=/app/out/result.txt
if [ -s "$in" ]; then cat "$in" > "$out"; else : > "$out"; fi
printf '%s\n' "report" >> /app/out/order.log
