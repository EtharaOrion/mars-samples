#!/bin/sh
mkdir -p /logs/verifier 2>/dev/null || true
D=$(dirname "$0")
rc=1
if python3 "$D/check_healthy_and_result.py" && python3 "$D/check_ordering_and_integrity.py"; then
  rc=0
fi
if [ $rc -eq 0 ]; then echo 1 > /logs/verifier/reward.txt 2>/dev/null || true; else echo 0 > /logs/verifier/reward.txt 2>/dev/null || true; fi
exit $rc
