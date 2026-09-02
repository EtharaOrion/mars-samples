#!/bin/bash
# Harbor verifier entrypoint.  Runs after the agent phase, in the same
# container.  Delegates to grader.py which writes the reward contract JSON.
set -uo pipefail
export LC_ALL=C

REWARD_PATH="${TB_REWARD_CONTRACT_PATH:-/logs/verifier/reward.json}"
export REWARD_PATH

python3 /tests/grader.py
rc=$?

# Fail-closed: if grader did not write a non-empty reward file, plant a zero
# reward with a machine-readable reason so Harbor's rule 8 is satisfied.
if [ ! -s "$REWARD_PATH" ]; then
    mkdir -p "$(dirname "$REWARD_PATH")"
    printf '{"reward": 0.0, "reason": "grader_crashed_or_wrote_no_reward"}\n' \
        > "$REWARD_PATH"
fi

exit $rc
