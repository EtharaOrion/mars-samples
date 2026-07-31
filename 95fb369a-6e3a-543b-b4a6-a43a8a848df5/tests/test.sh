#!/bin/sh
mkdir -p /logs/verifier
ready=0
i=0
while [ $i -lt 20 ]; do
  if python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)" 2>/dev/null; then
    ready=1
    break
  fi
  i=$((i+1))
  sleep 0.5
done
rc=1
if [ $ready -eq 1 ]; then
  if python3 /tests/check_endpoints.py && python3 /tests/check_security.py; then
    rc=0
  fi
fi
if [ $rc -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
exit $rc
