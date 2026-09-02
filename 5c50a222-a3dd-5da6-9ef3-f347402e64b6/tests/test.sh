#!/bin/bash
set -uo pipefail
export LC_ALL=C

REWARD_PATH="${TB_REWARD_CONTRACT_PATH:-/logs/verifier/reward.json}"
export REWARD_PATH

python3 /tests/grader.py
rc=$?

if [ ! -s "$REWARD_PATH" ]; then
    mkdir -p "$(dirname "$REWARD_PATH")"
    printf '{"reward": 0.0, "reason": "grader_crashed_or_wrote_no_reward"}\n' \
        > "$REWARD_PATH"
fi

exit $rc
