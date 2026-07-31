#!/bin/sh
set -e
cd /app

check() {
  want="$1"; file="$2"
  got=$(sha256sum "$file" | awk '{print $1}')
  if [ "$got" != "$want" ]; then echo "REDLINE: $file was modified"; exit 1; fi
}
# RED LINE RL1: crate source + build script must be byte-identical to shipped.
check 620571f2387a5f62ecbca8da77357c978fa56d625cbd7921c6f27a5cc2d35059 src/lib.rs
check 7ba6c105ada0d255644a9af92db9e5e3c7c39de9b6977a74bc00a79ac17b74ca src/main.rs
check 33dab7924d8f73088a0d8c7ae938b8efcec5f8f74cded3fff556404fe6485cf8 build.rs

# Prove it is a genuine cross-compile: target arch must differ from host arch.
host=$(uname -m)
if [ "$host" != "x86_64" ]; then echo "UNEXPECTED_HOST_ARCH: $host"; exit 1; fi
BIN=target/aarch64-unknown-linux-gnu/release/star14
test -f "$BIN" || { echo "MISSING_TARGET_BINARY: $BIN"; exit 1; }
machine=$(od -An -tx1 -j18 -N2 "$BIN" | tr -d ' ')
if [ "$machine" = "3e00" ]; then echo "NOT_CROSS: target is host x86_64"; exit 1; fi
if [ "$machine" != "b700" ]; then echo "WRONG_TARGET_ARCH: $machine"; exit 1; fi
echo "OK_INTEGRITY"
