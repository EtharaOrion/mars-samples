#!/bin/sh
set -e
cd /app
check() {
  want="$1"; file="$2"
  got=$(sha256sum "$file" | awk '{print $1}')
  if [ "$got" != "$want" ]; then echo "REDLINE: $file was modified"; exit 1; fi
}
check 6e61c0dac253adc98b126052e96c323efb1401f7fdadd124e93f28da00f99296 src/lib.rs
check 86c8317480f9bd24e68d48e2e3bdde06f37fc29ce3132413a269d2a996a39b9f src/main.rs
check b977c05f4323dabde34b40206e7640f516c633b8fed91cbaff3818070f1e3358 tests/feature_test.rs
