#!/bin/sh
set -e
cd /app
rm -rf bazel-bin bazel-out
python3 build.py //...
test -x bazel-bin/cmd/app/app
out=$(./bazel-bin/cmd/app/app)
expected="app total=34 sum=34 product=3003"
if [ "$out" != "$expected" ]; then
    echo "BAD_OUTPUT: got [$out] want [$expected]"
    exit 1
fi
test -f bazel-bin/libs/mathx/mathx_test.testresult
grep -q PASS bazel-bin/libs/mathx/mathx_test.testresult
