#!/bin/bash
set -euo pipefail

REWARD_JSON=/logs/verifier/reward.json
mkdir -p /logs/verifier

exec python3 /tests/grader.py "$REWARD_JSON" 2>&1
