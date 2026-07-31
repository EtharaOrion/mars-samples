#!/bin/sh
mkdir -p /logs/verifier 2>/dev/null || true
TESTDIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rc=1
if python3 "$TESTDIR/check_order_result.py" && python3 "$TESTDIR/check_cache_and_integrity.py"; then
  rc=0
fi
if [ -d /logs/verifier ]; then
  if [ $rc -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
fi
exit $rc
