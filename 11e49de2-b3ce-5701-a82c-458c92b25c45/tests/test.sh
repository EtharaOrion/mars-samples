#!/bin/bash
# Harbor verifier entrypoint.  Runs after the agent phase, in the same
# container.  Delegates to grader.py which writes the reward contract JSON to
# the path Harbor expects.
set -uo pipefail
export LC_ALL=C
export PATH=/usr/lib/postgresql/16/bin:$PATH

REWARD_PATH="${TB_REWARD_CONTRACT_PATH:-/logs/verifier/reward.json}"
export REWARD_PATH

# Delegate to grader; grader is responsible for ALL zero-score attribution and
# for writing the reward file even on early exit paths.
python3 /tests/grader.py
rc=$?

# Fail-closed: if grader failed to write reward, plant a zero-reward with a
# machine-readable reason.
if [ ! -s "$REWARD_PATH" ]; then
  mkdir -p "$(dirname "$REWARD_PATH")"
  printf '{"reward": 0.0, "reason": "grader_crashed_or_wrote_no_reward"}\n' \
      > "$REWARD_PATH"
fi

exit $rc
