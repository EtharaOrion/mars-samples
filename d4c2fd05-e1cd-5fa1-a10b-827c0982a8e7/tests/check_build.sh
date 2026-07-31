#!/bin/sh
set -e
cd /app
go build ./...
go vet ./...
go build -o /tmp/greeter .
test -x /tmp/greeter
out=$(/tmp/greeter)
expected="greeter sum-of-squares v1.4.2 compute(10)=385"
if [ "$out" != "$expected" ]; then echo "BAD_OUTPUT: $out"; exit 1; fi
