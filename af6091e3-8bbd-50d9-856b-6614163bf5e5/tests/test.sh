#!/bin/sh
d=$(dirname "$0")
mkdir -p /logs/verifier 2>/dev/null || true
rc=1
if python3 "$d/check_rootless_uid_mapping.py" && python3 "$d/check_unprivileged_and_integrity.py"; then
  rc=0
fi
if [ -d /logs/verifier ] 2>/dev/null; then
  if [ $rc -eq 0 ]; then echo 1 > /logs/verifier/reward.txt 2>/dev/null || true; else echo 0 > /logs/verifier/reward.txt 2>/dev/null || true; fi
fi
exit $rc
