#!/bin/sh
set -e
cd /app

# The cross build must succeed, offline, with exit 0.
export CARGO_NET_OFFLINE=true
cargo build --release --target aarch64-unknown-linux-gnu

BIN=target/aarch64-unknown-linux-gnu/release/star14
test -f "$BIN" || { echo "MISSING_TARGET_BINARY: $BIN"; exit 1; }

# ELF magic: bytes 0..3 == 7f 45 4c 46
magic=$(od -An -tx1 -j0 -N4 "$BIN" | tr -d ' ')
if [ "$magic" != "7f454c46" ]; then echo "NOT_ELF: $magic"; exit 1; fi

# ELF e_machine at offset 0x12 (18), 2 bytes little-endian.
# EM_AARCH64 == 0xB7 -> bytes "b7 00".
machine=$(od -An -tx1 -j18 -N2 "$BIN" | tr -d ' ')
if [ "$machine" != "b700" ]; then
  echo "WRONG_ARCH: e_machine=$machine (expected b700 EM_AARCH64)"; exit 1
fi
echo "OK_AARCH64"
