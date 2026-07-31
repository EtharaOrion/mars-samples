#!/bin/sh
set -e
cd /app

# RED LINE RL1: Go sources, the test file, and the build runner must be
# byte-identical to the shipped state. Only BUILD graph files may change.
check() {
    got=$(sha256sum "$1" | awk '{print $1}')
    if [ "$got" != "$2" ]; then
        echo "REDLINE: protected file modified: $1"
        exit 1
    fi
}
check libs/mathx/mathx.go      2b485d1a61fa8062b8fc77bd610b02850b66a3c4dcb578b88aa883fc1d9f6923
check libs/mathx/mathx_test.go c7cc57a4960161f593bd220de4188a1f9281731f09928d9d010cc228244f7d31
check libs/report/report.go    7748d48be20c9facc1a33e4c9f9b675fa9a5bcedaaf58455b707cac19fce1d0d
check cmd/app/main.go          66197c0bb38287895422c38e6d9ac0e603d763409d4b86004da5697eedd13dd8
check build.py                 19b7aee1bfb7dd404b63678354cc83ba763a659e240a2b976e145aa0f43e669b

# ORDER EVIDENCE: the multi-target graph must have been built in dependency
# order. Parse the build log emitted by build.py and require the topological
# precedence mathx -> report -> app and mathx -> mathx_test.
log=bazel-out/build.log
test -f "$log"
grep -q '^OK$' "$log" || { echo "INTEGRITY: build did not complete OK"; exit 1; }
idx() { awk -v L="$1" '$1=="BUILT" && $3==L {print $2; exit}' "$log"; }
mi=$(idx //libs/mathx:mathx)
ri=$(idx //libs/report:report)
ai=$(idx //cmd/app:app)
ti=$(idx //libs/mathx:mathx_test)
if [ -z "$mi" ] || [ -z "$ri" ] || [ -z "$ai" ] || [ -z "$ti" ]; then
    echo "INTEGRITY: expected targets missing from build log"
    exit 1
fi
if [ "$mi" -ge "$ri" ] || [ "$ri" -ge "$ai" ] || [ "$mi" -ge "$ai" ] || [ "$mi" -ge "$ti" ]; then
    echo "INTEGRITY: targets not built in dependency order"
    exit 1
fi
