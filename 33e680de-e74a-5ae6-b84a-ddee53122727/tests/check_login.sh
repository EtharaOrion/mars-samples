#!/bin/sh
set -u
out=$(bash -lc greet 2>/dev/null); rc=$?
if [ "$rc" -ne 0 ]; then echo "LOGIN_EXIT:$rc"; exit 1; fi
if [ "$out" != "hello from greet" ]; then echo "LOGIN_OUT:[$out]"; exit 1; fi
exit 0
