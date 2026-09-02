#!/bin/bash
set -u

REWARD_DIR="/logs/verifier"
REWARD_JSON="${REWARD_DIR}/reward.json"
mkdir -p "$REWARD_DIR"

python3 /tests/run_prosecutor_judge.py > "$REWARD_JSON" 2>/logs/verifier/verifier.log
