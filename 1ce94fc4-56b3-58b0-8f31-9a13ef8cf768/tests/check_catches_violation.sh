#!/bin/sh
# WITHHELD: running the configured hooks over a tree containing a planted
# violation must FAIL (non-zero) and must NAME the offending token.
set -u
TOKEN="TODO_FIXME_BANNED"
WORK="$(mktemp -d)"
cp -a /app/. "$WORK/"
rm -rf "$WORK/.git" "$WORK/.pccache"
cp /tests/fixtures/violation_sample.py "$WORK/src/violation_sample.py"
OUT="$(mktemp)"
( cd "$WORK" && bash run_hooks.sh ) > "$OUT" 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
    echo "check_catches_violation: hooks exited 0 on a planted violation (silent no-op)"
    echo "--- hook output ---"; cat "$OUT"
    rm -rf "$WORK" "$OUT"; exit 1
fi
if ! grep -q "$TOKEN" "$OUT"; then
    echo "check_catches_violation: hooks failed but did not name the violation ($TOKEN)"
    echo "--- hook output ---"; cat "$OUT"
    rm -rf "$WORK" "$OUT"; exit 1
fi
echo "check_catches_violation: ok"
rm -rf "$WORK" "$OUT"
exit 0
