#!/bin/sh
LOGDIR="${LOGDIR:-/logs/verifier}"
mkdir -p "$LOGDIR"
here=$(dirname "$0")
rc=1
if python3 "$here/check_app_output.py" && python3 "$here/check_size_and_integrity.py"; then
  rc=0
fi
if [ "$rc" -eq 0 ]; then echo 1 > "$LOGDIR/reward.txt"; else echo 0 > "$LOGDIR/reward.txt"; fi
exit $rc
