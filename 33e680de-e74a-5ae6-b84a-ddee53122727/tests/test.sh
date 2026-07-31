#!/bin/sh
set -u
mkdir -p /logs/verifier
ok=1
sh /tests/check_login.sh || ok=0
sh /tests/check_nonlogin.sh || ok=0
if [ "$ok" = 1 ]; then echo 1 > /logs/verifier/reward.txt; exit 0; fi
echo 0 > /logs/verifier/reward.txt; exit 1
