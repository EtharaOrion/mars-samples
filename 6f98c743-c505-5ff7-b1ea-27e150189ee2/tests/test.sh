#!/usr/bin/env bash
set -euo pipefail

REWARD_DIR="${REWARD_DIR:-/logs/verifier}"
mkdir -p "${REWARD_DIR}"

python3 /tests/grader.py
