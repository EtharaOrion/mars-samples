#!/bin/sh
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p /logs/verifier 2>/dev/null || true
rc=1
if python3 "$here/check_roundtrip.py" && python3 "$here/check_offline_and_integrity.py"; then
  rc=0
fi
if [ $rc -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt 2>/dev/null || true
else
  echo 0 > /logs/verifier/reward.txt 2>/dev/null || true
fi
exit $rc
