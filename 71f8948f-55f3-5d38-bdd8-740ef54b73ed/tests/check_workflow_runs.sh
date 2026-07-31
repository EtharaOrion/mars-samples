#!/bin/sh
# World-state check: the offline runner executes ci.yml end-to-end and the
# real build+test produce the golden artifact and the test-pass marker.
set -e
cd /app
rm -f _runlog.txt
rm -rf out
python3 run-workflow .github/workflows/ci.yml
test -f out/app.txt || { echo "FAIL: build artifact out/app.txt missing"; exit 1; }
want="99925beb2cae56ed2627094818c5cb80e0298647ca4f9587f4387ef6f91fcc22"
got=$(sha256sum out/app.txt | awk '{print $1}')
if [ "$got" != "$want" ]; then
  echo "FAIL: out/app.txt content not golden"
  echo "----- got -----"; cat out/app.txt
  exit 1
fi
test -f out/tests.ok || { echo "FAIL: test-pass marker out/tests.ok missing"; exit 1; }
echo "PASS check_workflow_runs"
