#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
exec python3 /tests/grader.py /logs/verifier/reward.json 2>&1
