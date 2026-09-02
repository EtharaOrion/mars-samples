#!/usr/bin/env bash
# FORGE verifier for cli-awk-fixed-width-with-embedded-escapes
# Container-local grading. Writes /logs/verifier/reward.json.
# Failure taxonomy: D1, D2, D3, D4, D5.

set -u

LOG_DIR="/logs/verifier"
REWARD_JSON="${LOG_DIR}/reward.json"
mkdir -p "${LOG_DIR}"

SOLVE="/workspace/solve.sh"
PUBLIC_DATA="/workspace/data.txt"
PUBLIC_EXPECTED="/workspace/expected_output.txt"
HOLDOUT_DATA="/verifier/holdout.txt"
HOLDOUT_EXPECTED="/verifier/holdout_expected.txt"

# The verifier tree is expected to be materialized at /verifier by the
# harness before this script runs. If it is not, we materialize it from
# tests/ so a stand-alone shell invocation of test.sh from the bundle root
# also works.
if [ ! -f "${HOLDOUT_DATA}" ]; then
  SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
  mkdir -p /verifier
  cp "${SELF_DIR}/holdout.txt" "${HOLDOUT_DATA}"
  cp "${SELF_DIR}/holdout_expected.txt" "${HOLDOUT_EXPECTED}"
fi

emit_reward() {
  local reward="$1"
  local reason="$2"
  local extra="$3"
  cat > "${REWARD_JSON}" <<JSON
{
  "reward": ${reward},
  "reason": "${reason}",
  "prosecutor": ${extra}
}
JSON
  echo "REWARD=${reward} REASON=${reason}"
  exit 0
}

# --- D1: solve.sh presence, non-empty, executable ---
if [ ! -f "${SOLVE}" ] || [ ! -s "${SOLVE}" ] || [ ! -x "${SOLVE}" ]; then
  emit_reward 0.0 "D1_solve_sh_absent_or_empty_or_not_executable" \
    "{\"solve_sh_present_and_nonempty_and_executable\": false}"
fi

# --- D5: byte-scan solve.sh for bound shortcut patterns ---
# Patterns (Python-flavored regex, ASCII word boundaries).
PATTERNS=(
  '\bpython3?\b'
  '\bperl\b'
  '\bsed\b'
  '\bruby\b'
  '\bcut\b'
  '\bcolumn\b'
  '\btr\b'
  '\bmawk\b'
  '\bcat\s+[^|<]*expected'
  '\bcat\s+/verifier'
  '\bcp\s+[^|<]*expected'
)
MATCHED_PATTERN=""
for pat in "${PATTERNS[@]}"; do
  if python3 -c "
import re, sys
pat = sys.argv[1]
with open(sys.argv[2], 'rb') as f:
    data = f.read().decode('utf-8', errors='replace')
m = re.search(pat, data)
sys.exit(0 if m else 1)
" "${pat}" "${SOLVE}"; then
    MATCHED_PATTERN="${pat}"
    break
  fi
done
if [ -n "${MATCHED_PATTERN}" ]; then
  MATCHED_JSON_ESC=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${MATCHED_PATTERN}")
  emit_reward 0.0 "D5_solve_sh_matches_a_bound_shortcut_pattern" \
    "{\"solve_sh_no_bound_shortcut_pattern\": false, \"matched_shortcut_pattern\": ${MATCHED_JSON_ESC}}"
fi

# --- D2: solve.sh runs on public data with exit=0 and non-empty stdout ---
PUBLIC_STDOUT="$(bash "${SOLVE}" "${PUBLIC_DATA}" 2>/dev/null || true)"
PUBLIC_RC=$?
# rc is unreliable here because of the "|| true", capture properly:
bash "${SOLVE}" "${PUBLIC_DATA}" > /tmp/pub_out.txt 2> /tmp/pub_err.txt
PUBLIC_RC=$?
PUBLIC_STDOUT="$(cat /tmp/pub_out.txt)"
if [ "${PUBLIC_RC}" -ne 0 ] || [ -z "${PUBLIC_STDOUT}" ]; then
  emit_reward 0.0 "D2_solve_sh_exit_nonzero_or_no_output_on_public_data" \
    "{\"bash_returncode_on_public_data\": ${PUBLIC_RC}, \"public_emitted_line_count\": $(echo -n "${PUBLIC_STDOUT}" | grep -c '^' || echo 0)}"
fi

# --- D3: public stdout equals expected column-three sequence (ordered equality) ---
NORMALIZE_PY='
import sys, pathlib
def norm(s):
    lines = s.split("\n")
    # strip trailing CR from each line
    lines = [l[:-1] if l.endswith("\r") else l for l in lines]
    # drop trailing empty lines (from a trailing newline on last content line)
    while lines and lines[-1] == "":
        lines.pop()
    # trim leading/trailing ASCII space and tab from each line
    trimmed = [l.strip(" \t") for l in lines]
    return trimmed

actual = norm(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = norm(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
if len(actual) != len(expected):
    print(f"LENGTH_MISMATCH actual={len(actual)} expected={len(expected)}")
    sys.exit(2)
for i, (a, e) in enumerate(zip(actual, expected)):
    if a != e:
        print(f"FIRST_MISMATCH index={i} actual={a!r} expected={e!r}")
        sys.exit(3)
print(f"MATCH lines={len(expected)}")
sys.exit(0)
'
PUB_CMP="$(python3 -c "${NORMALIZE_PY}" /tmp/pub_out.txt "${PUBLIC_EXPECTED}" || true)"
if ! echo "${PUB_CMP}" | grep -q "^MATCH"; then
  PUB_CMP_JSON=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${PUB_CMP}")
  emit_reward 0.0 "D3_public_stdout_fails_ordered_equality_against_expected_column_three_sequence" \
    "{\"bash_returncode_on_public_data\": ${PUBLIC_RC}, \"public_diff\": ${PUB_CMP_JSON}}"
fi

# --- D4: private holdout stdout equals expected column-three sequence ---
bash "${SOLVE}" "${HOLDOUT_DATA}" > /tmp/hld_out.txt 2> /tmp/hld_err.txt
HLD_RC=$?
if [ "${HLD_RC}" -ne 0 ]; then
  emit_reward 0.0 "D4_private_holdout_stdout_fails_ordered_equality_against_expected_column_three_sequence" \
    "{\"bash_returncode_on_holdout_data\": ${HLD_RC}}"
fi
HLD_CMP="$(python3 -c "${NORMALIZE_PY}" /tmp/hld_out.txt "${HOLDOUT_EXPECTED}" || true)"
if ! echo "${HLD_CMP}" | grep -q "^MATCH"; then
  HLD_CMP_JSON=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${HLD_CMP}")
  emit_reward 0.0 "D4_private_holdout_stdout_fails_ordered_equality_against_expected_column_three_sequence" \
    "{\"bash_returncode_on_holdout_data\": ${HLD_RC}, \"holdout_diff\": ${HLD_CMP_JSON}}"
fi

# --- all passed ---
emit_reward 1.0 "all_deliverables_passed" \
  "{\"solve_sh_present_and_nonempty_and_executable\": true, \"solve_sh_no_bound_shortcut_pattern\": true, \"bash_returncode_on_public_data\": ${PUBLIC_RC}, \"bash_returncode_on_holdout_data\": ${HLD_RC}}"
