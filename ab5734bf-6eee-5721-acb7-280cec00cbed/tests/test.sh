#!/bin/sh
mkdir -p /logs/verifier
sh /tests/check_report.sh && sh /tests/check_integrity.sh
rc=$?
if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
exit "$rc"
