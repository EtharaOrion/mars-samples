"""Grader for pipe-jq-sed-awk-pipeline-order-matters (revision 2).

Runs D1 through D7 against the agent output at /workspace/out/critical.tsv
and writes the reward JSON to /logs/verifier/reward.json.

Revision 2 changes vs revision 1:
  - D5 forbid-list extended to cover the hardcoded-recital vector (bytes
    referencing /tests/grader.py, EXPECTED_LINES, from-grader-import, sys.path
    insertion pointing into /tests, and importlib module-resolution of grader).
  - New D7 pipeline-structure check: solve.sh must contain a jq | sed | awk
    pipeline whose stages appear in that order, joined by literal | operators.
    Comment-only lines and bash backslash-newline continuations are folded
    before matching so a legitimate multi-line pipeline still matches, but a
    decoy `# jq | sed | awk` in a comment cannot satisfy the check.
  - D3 reference set expanded to include an adversarial row whose path holds
    'test' only as an intra-segment substring (never as a whole /-delimited
    segment). A solver that drops rows with `sed '/test/d'` or `grep -v test`
    loses this row and fails set equality even if it satisfies D7.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("PIPE_JQ_OUTPUT", "/workspace/out/critical.tsv"))
SOLVE_SCRIPT_PATH = Path(os.environ.get("PIPE_JQ_SOLVE_SCRIPT", "/workspace/solve.sh"))
REWARD_PATH = Path(os.environ.get("REWARD_PATH", "/logs/verifier/reward.json"))

SOLVE_SCRIPT_LINE_BUDGET = 60

FIELD_1_REGEX = re.compile(r"^(@[a-z0-9][a-z0-9._-]{0,213}/[a-z0-9][a-z0-9._-]{0,213}|[a-z0-9][a-z0-9._-]{0,213})$")
FIELD_2_REGEX = re.compile(r"^v?[0-9]+(\.[0-9]+){0,2}([-+][0-9A-Za-z.-]+)?$")
FIELD_3_REGEX = re.compile(r"^GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}$")
FIELD_4_REGEX = re.compile(r"^[.]?node_modules(/[^/\t]+)+$")

CANARY_TOKEN_REGEX = re.compile(rb"FORGE_HOLDOUT_CANARY_[A-Z0-9]{32}")

FORBIDDEN_SOLVE_PATTERNS_BYTES = [
    (re.compile(rb"FORGE_HOLDOUT_CANARY_[A-Z0-9]{32}"),        "canary_token"),
    (re.compile(rb"solution/grounding\.yaml"),                 "grounding_yaml_path"),
    (re.compile(rb"solution/TRUTH\.md"),                       "truth_md_path"),
    (re.compile(rb"dataset/[0-9a-f-]{36}/(solution|tests)/"),  "dataset_holdout_path"),
    (re.compile(rb"/holdout/"),                                "holdout_slash"),
    (re.compile(rb"HARDCODED_CRITICAL_VULN_RECITAL_BEGIN"),    "hardcoded_recital_begin"),
    (re.compile(rb"HARDCODED_CRITICAL_VULN_RECITAL_END"),      "hardcoded_recital_end"),
    (re.compile(rb"reference_critical_vuln_set"),              "grounding_key_reference_set"),
    (re.compile(rb"canonical_output_form"),                    "grounding_key_canonical_form"),
    (re.compile(rb"test_path_regex"),                          "grounding_key_test_path_regex"),
    # Revision 2 additions: bind out the hardcoded_heredoc_recital vector.
    (re.compile(rb"/tests/grader\.py"),                        "runtime_grader_path"),
    (re.compile(rb"\bEXPECTED_LINES\b"),                       "runtime_expected_lines_symbol"),
    (re.compile(rb"from\s+grader\s+import"),                   "runtime_from_grader_import"),
    (re.compile(rb"sys\.path\.insert\s*\([^)]*['\"]/?tests"),  "runtime_sys_path_insert_tests"),
    (re.compile(rb"sys\.path\.append\s*\([^)]*['\"]/?tests"),  "runtime_sys_path_append_tests"),
    (re.compile(rb"import\s+importlib.*\.import_module\s*\(\s*['\"]grader"),
                                                                "runtime_importlib_import_grader"),
]


# --- reference critical vulnerability set (embedded, no runtime file dependency)
EXPECTED_LINES = [
    '@angular/core\t13.2.7\tGHSA-a1b2-c3d4-e5f6\tnode_modules/@angular/core',
    '@babel/core\t7.16.0\tGHSA-b2c3-d4e5-f6a7\tnode_modules/@babel/core',
    '@nestjs/common\t8.4.2\tGHSA-c3d4-e5f6-a7b8\tnode_modules/@nestjs/common',
    '@types/node\t16.11.7\tGHSA-d4e5-f6a7-b8c9\tnode_modules/@types/node',
    'axios\t0.21.1\tGHSA-e5f6-a7b8-c9d0\tnode_modules/axios',
    'backtest-lib\t2.4.0\tGHSA-b8k9-t3st-l1b0\tnode_modules/backtest-lib',
    'body-parser\t1.19.0\tGHSA-f6a7-b8c9-d0e1\tnode_modules/express/node_modules/body-parser',
    'chalk\t4.1.0\tGHSA-a7b8-c9d0-e1f2\tnode_modules/chalk',
    'commander\t7.2.0\tGHSA-b8c9-d0e1-f2a3\tnode_modules/commander',
    'debug\t4.3.1\tGHSA-c9d0-e1f2-a3b4\tnode_modules/debug',
    'express\t4.17.1\tGHSA-d0e1-f2a3-b4c5\tnode_modules/express',
    'fs-extra\t9.1.0\tGHSA-e1f2-a3b4-c5d6\tnode_modules/fs-extra',
    'lodash\t4.17.20\tGHSA-p6mc-m468-83gw\tnode_modules/lodash',
    'marked\t1.2.9\tGHSA-2c8b-2c9d-4a5e\tnode_modules/marked',
    'minimist\t1.2.5\tGHSA-vh95-rmgr-6w4m\tnode_modules/minimist',
    'moment\t2.29.1\tGHSA-8hfj-j24r-96c4\tnode_modules/moment',
    'node-fetch\t2.6.6\tGHSA-r683-j2x4-v87g\tnode_modules/node-fetch',
    'semver\t7.3.5\tGHSA-c2qf-rxjj-qqgw\tnode_modules/semver',
    'tar\t6.1.0\tGHSA-r628-mhmh-qjhw\tnode_modules/tar',
    'typescript\t4.5.4\tGHSA-7ppw-8cmc-4vfr\tnode_modules/typescript',
    'ws\t7.4.5\tGHSA-6fc8-4gx4-v693\tnode_modules/ws',
]


def _reward(success: bool, reason: str, breakdowns: dict[str, dict[str, object]]) -> None:
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "reward": 1.0 if success else 0.0,
        "success": bool(success),
        "reason": reason,
        "breakdown": breakdowns,
    }
    REWARD_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def d1_output_exists() -> tuple[bool, dict[str, object]]:
    if not OUTPUT_PATH.is_file():
        return False, {"reason": f"missing output at {OUTPUT_PATH}"}
    data = OUTPUT_PATH.read_bytes()
    size = len(data)
    if size == 0:
        return False, {"path": str(OUTPUT_PATH), "size": 0, "reason": "empty_output"}
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as e:
        return False, {"path": str(OUTPUT_PATH), "size": size, "reason": f"invalid_utf8:{e}"}
    if not data.endswith(b"\n"):
        return False, {"path": str(OUTPUT_PATH), "size": size, "reason": "missing_trailing_newline"}
    return True, {"path": str(OUTPUT_PATH), "size": size}


def d2_row_shape_invariant(actual_bytes: bytes) -> tuple[bool, dict[str, object]]:
    text = actual_bytes.decode("utf-8", errors="replace")
    lines = [ln for ln in text.split("\n") if ln != ""]
    first_violation = None
    for i, line in enumerate(lines, 1):
        parts = line.split("\t")
        if len(parts) != 4:
            first_violation = {"row_index": i, "reason": "wrong_field_count", "observed_field_count": len(parts), "observed_line": line[:200]}
            break
        for j, (part, regex, label) in enumerate(zip(parts, (FIELD_1_REGEX, FIELD_2_REGEX, FIELD_3_REGEX, FIELD_4_REGEX), ("package_name", "installed_version", "ghsa_id", "node_modules_path")), 1):
            if part == "":
                first_violation = {"row_index": i, "field_index": j, "field_label": label, "reason": "empty_field", "observed_value": ""}
                break
            if not regex.match(part):
                first_violation = {"row_index": i, "field_index": j, "field_label": label, "reason": "regex_mismatch", "observed_value": part[:200]}
                break
        if first_violation is not None:
            break
    return first_violation is None, {"row_count": len(lines), "first_violation": first_violation}


def d3_set_equality(actual_bytes: bytes) -> tuple[bool, dict[str, object]]:
    text = actual_bytes.decode("utf-8", errors="replace")
    actual_lines = [ln for ln in text.split("\n") if ln != ""]
    actual_set = set(actual_lines)
    expected_set = set(EXPECTED_LINES)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    return (len(missing) == 0 and len(extra) == 0), {
        "actual_count": len(actual_lines),
        "expected_count": len(EXPECTED_LINES),
        "missing_entries": missing[:20],
        "extra_entries": extra[:20],
        "missing_total": len(missing),
        "extra_total": len(extra),
    }


def d4_row_ordering(actual_bytes: bytes) -> tuple[bool, dict[str, object]]:
    text = actual_bytes.decode("utf-8", errors="replace")
    lines = [ln for ln in text.split("\n") if ln != ""]
    inversions = 0
    first_inv = None
    prev_key = None
    for i, line in enumerate(lines, 1):
        parts = line.split("\t")
        if len(parts) < 2:
            key = (line, "")
        else:
            key = (parts[0], parts[1])
        if prev_key is not None and key < prev_key:
            inversions += 1
            if first_inv is None:
                first_inv = {"pair_index": i - 1, "prev_key": list(prev_key), "this_key": list(key)}
        prev_key = key
    return inversions == 0, {"inversions": inversions, "first_inversion": first_inv}


def d5_solve_script_shortcut_scan() -> tuple[bool, dict[str, object]]:
    if not SOLVE_SCRIPT_PATH.is_file():
        return False, {"reason": "solve_script_missing", "path": str(SOLVE_SCRIPT_PATH)}
    script_bytes = SOLVE_SCRIPT_PATH.read_bytes()
    hits = []
    for regex, label in FORBIDDEN_SOLVE_PATTERNS_BYTES:
        m = regex.search(script_bytes)
        if m:
            hits.append({"pattern": label, "byte_offset": m.start(), "matched_bytes": m.group().decode("utf-8", errors="replace")[:200]})
    return len(hits) == 0, {"hits": hits}


def d6_solve_script_line_budget() -> tuple[bool, dict[str, object]]:
    if not SOLVE_SCRIPT_PATH.is_file():
        return False, {"reason": "solve_script_missing", "path": str(SOLVE_SCRIPT_PATH)}
    data = SOLVE_SCRIPT_PATH.read_bytes()
    newlines = data.count(b"\n")
    tail = 0 if data.endswith(b"\n") else 1
    line_count = newlines + tail
    ok = line_count <= SOLVE_SCRIPT_LINE_BUDGET
    return ok, {"line_count": line_count, "budget": SOLVE_SCRIPT_LINE_BUDGET}


# --- D7: positive pipeline-structure invariant on solve.sh
_D7_PIPELINE_PATTERN = re.compile(
    r"\bjq\b[^\n|]*\|[^\n]*?\bsed\b[^\n|]*\|[^\n]*?\b(?:g?awk|mawk)\b"
)


def _fold_solve_script_for_structure(text: str) -> str:
    """Strip comment-only lines and fold backslash-newline continuations into
    one logical line per bash pipeline."""
    kept = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        kept.append(line)
    joined = "\n".join(kept)
    return re.sub(r"\\\n[ \t]*", " ", joined)


def d7_pipeline_structure() -> tuple[bool, dict[str, object]]:
    if not SOLVE_SCRIPT_PATH.is_file():
        return False, {"reason": "solve_script_missing", "path": str(SOLVE_SCRIPT_PATH)}
    text = SOLVE_SCRIPT_PATH.read_text(encoding="utf-8", errors="replace")
    logical = _fold_solve_script_for_structure(text)
    m = _D7_PIPELINE_PATTERN.search(logical)
    if m is None:
        return False, {
            "reason": "D7_pipeline_structure_missing_jq_pipe_sed_pipe_awk_ordered_stages",
            "checked_pattern": _D7_PIPELINE_PATTERN.pattern,
        }
    return True, {"matched_span": [m.start(), m.end()], "matched_bytes": m.group()[:200]}


REASON_MAP = {
    "D1": "D1_output_file_missing_or_empty_or_invalid_utf8",
    "D2": "D2_row_shape_invariant_violation",
    "D3": "D3_output_line_set_mismatch_with_reference",
    "D4": "D4_row_ordering_violation",
    "D5": "D5_solve_script_matches_bound_shortcut_pattern",
    "D6": "D6_solve_script_line_count_exceeds_budget",
    "D7": "D7_pipeline_structure_missing_jq_pipe_sed_pipe_awk_ordered_stages",
}


def main() -> int:
    breakdown: dict[str, dict[str, object]] = {}

    ok_d1, det_d1 = d1_output_exists()
    breakdown["D1_output_exists"] = {"pass": ok_d1, **det_d1}
    if not ok_d1:
        _reward(False, REASON_MAP["D1"], breakdown)
        return 1

    actual = OUTPUT_PATH.read_bytes()

    ok_d2, det_d2 = d2_row_shape_invariant(actual)
    breakdown["D2_row_shape_invariant"] = {"pass": ok_d2, **det_d2}

    ok_d3, det_d3 = d3_set_equality(actual)
    breakdown["D3_set_equality"] = {"pass": ok_d3, **det_d3}

    ok_d4, det_d4 = d4_row_ordering(actual)
    breakdown["D4_row_ordering"] = {"pass": ok_d4, **det_d4}

    ok_d5, det_d5 = d5_solve_script_shortcut_scan()
    breakdown["D5_solve_script_shortcut_scan"] = {"pass": ok_d5, **det_d5}

    ok_d6, det_d6 = d6_solve_script_line_budget()
    breakdown["D6_solve_script_line_budget"] = {"pass": ok_d6, **det_d6}

    ok_d7, det_d7 = d7_pipeline_structure()
    breakdown["D7_pipeline_structure"] = {"pass": ok_d7, **det_d7}

    all_pass = all([ok_d1, ok_d2, ok_d3, ok_d4, ok_d5, ok_d6, ok_d7])
    if all_pass:
        reason = "all_deliverables_passed"
    else:
        for key, label in (
            ("D1_output_exists", "D1"),
            ("D2_row_shape_invariant", "D2"),
            ("D3_set_equality", "D3"),
            ("D4_row_ordering", "D4"),
            ("D5_solve_script_shortcut_scan", "D5"),
            ("D6_solve_script_line_budget", "D6"),
            ("D7_pipeline_structure", "D7"),
        ):
            if not breakdown[key]["pass"]:
                reason = REASON_MAP[label]
                break
        else:
            reason = "unknown_failure"

    _reward(all_pass, reason, breakdown)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
