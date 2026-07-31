#!/bin/sh
set -e
cd /app
cargo build --release
test -x ./target/release/star18
out=$(./target/release/star18)
expected="202739307150"
if [ "$out" != "$expected" ]; then echo "BAD_OUTPUT: $out"; exit 1; fi
cargo test --quiet
