#!/bin/sh
set -e
cd /app
make >/dev/null 2>&1
test -x ./app
out=$(./app)
expected="app coeff-model v2.3.1 compute(12)=996"
if [ "$out" != "$expected" ]; then
    echo "BAD_OUTPUT: got [$out] want [$expected]"
    exit 1
fi
