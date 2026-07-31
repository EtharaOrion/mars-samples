#!/bin/sh
mkdir -p /logs/verifier
sh /tests/check_catches_violation.sh && sh /tests/check_passes_clean_and_integrity.sh
rc=$?
if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
exit "$rc"
