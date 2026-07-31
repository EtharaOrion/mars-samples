#!/bin/sh
mkdir -p /logs/verifier
python3 /tests/check_installed.py && python3 /tests/check_offline_and_integrity.py
rc=$?
if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
exit "$rc"
