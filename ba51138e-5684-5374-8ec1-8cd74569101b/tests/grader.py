"""Grader for pipe-jstack-deadlock-vs-contention.

Runs D1 through D6 against the agent output at /workspace/out/report.tsv
and writes the reward JSON to /logs/verifier/reward.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("PIPE_JSTACK_OUTPUT", "/workspace/out/report.tsv"))
SOLVE_SCRIPT_PATH = Path(os.environ.get("PIPE_JSTACK_SOLVE_SCRIPT", "/workspace/solve.sh"))
REWARD_PATH = Path(os.environ.get("REWARD_PATH", "/logs/verifier/reward.json"))

SOLVE_SCRIPT_LINE_BUDGET = 90

ROW_TYPE_REGEX      = re.compile(r"^(DEADLOCKED_THREAD_COUNT|CONTENTION_THREAD_COUNT|DEADLOCK_LOCK|CONTENTION_LOCK)$")
COUNT_VALUE_REGEX   = re.compile(r"^(0|[1-9][0-9]*)$")
LOCK_ADDR_REGEX     = re.compile(r"^0x[0-9a-f]{16}$")

COUNT_PREFIXES = {"DEADLOCKED_THREAD_COUNT", "CONTENTION_THREAD_COUNT"}
LOCK_PREFIXES  = {"DEADLOCK_LOCK", "CONTENTION_LOCK"}

FORBIDDEN_SOLVE_PATTERNS_BYTES = [
    (re.compile(rb"FORGE_HOLDOUT_CANARY_[A-Z0-9]{32}"),        "canary_token"),
    (re.compile(rb"solution/grounding\.yaml"),                "grounding_yaml_path"),
    (re.compile(rb"solution/TRUTH\.md"),                      "truth_md_path"),
    (re.compile(rb"dataset/[0-9a-f-]{36}/(solution|tests)/"),  "dataset_holdout_path"),
    (re.compile(rb"/holdout/"),                                "holdout_slash"),
    (re.compile(rb"HARDCODED_REPORT_RECITAL_BEGIN"),           "hardcoded_recital_begin"),
    (re.compile(rb"HARDCODED_REPORT_RECITAL_END"),             "hardcoded_recital_end"),
    (re.compile(rb"reference_row_set"),                        "grounding_key_reference_row_set"),
    (re.compile(rb"reference_deadlock_locks"),                 "grounding_key_reference_deadlock_locks"),
    (re.compile(rb"reference_contention_locks"),               "grounding_key_reference_contention_locks"),
    (re.compile(rb"reference_deadlock_count"),                 "grounding_key_reference_deadlock_count"),
    (re.compile(rb"reference_contention_count"),               "grounding_key_reference_contention_count"),
    (re.compile(rb"canonical_output_form"),                    "grounding_key_canonical_output_form"),
    (re.compile(rb"per_field_schema_shape_regex_family"),      "grounding_key_per_field_schema"),
    (re.compile(rb"/tests/grader\.py"),                        "runtime_grader_path"),
    (re.compile(rb"EXPECTED_LINES"),                            "grader_expected_lines_constant"),
    (re.compile(rb"from\s+grader\s+import"),                   "grader_recital_import"),
    (re.compile(rb"sys\.path\.insert\s*\([^)]*['\"]/?tests"),  "sys_path_insert_tests"),
    (re.compile(rb"sys\.path\.append\s*\([^)]*['\"]/?tests"),  "sys_path_append_tests"),
]


# --- reference row set (embedded, no runtime file dependency) --------------
EXPECTED_LINES = [
    'DEADLOCKED_THREAD_COUNT\t3',
    'CONTENTION_THREAD_COUNT\t3',
    'DEADLOCK_LOCK\t0x00007fabc47a2b1c',
    'DEADLOCK_LOCK\t0x00007fabc4b53e91',
    'DEADLOCK_LOCK\t0x00007fabc4f108a7',
    'CONTENTION_LOCK\t0x00007fabc48c4d63',
    'CONTENTION_LOCK\t0x00007fabc4d691f8',
]


def _reward(success, reason, breakdowns):
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "reward": 1.0 if success else 0.0,
        "success": bool(success),
        "reason": reason,
        "breakdown": breakdowns,
    }
    REWARD_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def d1_output_exists():
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


def d2_row_shape_invariant(actual_bytes):
    text = actual_bytes.decode("utf-8", errors="replace")
    lines = [ln for ln in text.split("\n") if ln != ""]
    first_violation = None
    for i, line in enumerate(lines, 1):
        parts = line.split("\t")
        if len(parts) != 2:
            first_violation = {"row_index": i, "reason": "wrong_field_count", "observed_field_count": len(parts), "observed_line": line[:200]}
            break
        f1, f2 = parts[0], parts[1]
        if f1 == "" or f2 == "":
            first_violation = {"row_index": i, "reason": "empty_field", "observed_line": line[:200]}
            break
        if not ROW_TYPE_REGEX.match(f1):
            first_violation = {"row_index": i, "field_index": 1, "reason": "row_type_regex_mismatch", "observed_value": f1[:200]}
            break
        if f1 in COUNT_PREFIXES:
            if not COUNT_VALUE_REGEX.match(f2):
                first_violation = {"row_index": i, "field_index": 2, "reason": "count_value_regex_mismatch", "observed_value": f2[:200], "row_type": f1}
                break
        else:  # LOCK prefix
            if not LOCK_ADDR_REGEX.match(f2):
                first_violation = {"row_index": i, "field_index": 2, "reason": "lock_address_regex_mismatch", "observed_value": f2[:200], "row_type": f1}
                break
    return first_violation is None, {"row_count": len(lines), "first_violation": first_violation}


def d3_set_equality(actual_bytes):
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


def d4_row_ordering(actual_bytes):
    """Row 1 = DEADLOCKED_THREAD_COUNT, row 2 = CONTENTION_THREAD_COUNT,
    then a contiguous DEADLOCK_LOCK block ascending, then a contiguous
    CONTENTION_LOCK block ascending. No interleaving."""
    text = actual_bytes.decode("utf-8", errors="replace")
    lines = [ln for ln in text.split("\n") if ln != ""]
    first_violation = None

    def _fail(pos, reason, **kw):
        return {"position_index": pos, "reason": reason, **kw}

    if len(lines) < 2:
        return False, {"first_violation": _fail(len(lines), "too_few_rows")}

    parts0 = lines[0].split("\t")
    parts1 = lines[1].split("\t")
    if len(parts0) != 2 or parts0[0] != "DEADLOCKED_THREAD_COUNT":
        return False, {"first_violation": _fail(1, "row_1_prefix", expected="DEADLOCKED_THREAD_COUNT", observed=parts0[:1])}
    if len(parts1) != 2 or parts1[0] != "CONTENTION_THREAD_COUNT":
        return False, {"first_violation": _fail(2, "row_2_prefix", expected="CONTENTION_THREAD_COUNT", observed=parts1[:1])}

    # After the two count rows: DEADLOCK_LOCK block asc, then CONTENTION_LOCK block asc.
    saw_contention = False
    prev_deadlock = None
    prev_contention = None
    for i, line in enumerate(lines[2:], start=3):
        parts = line.split("\t")
        if len(parts) != 2:
            first_violation = _fail(i, "wrong_field_count", observed=parts[:1])
            break
        prefix, addr = parts[0], parts[1]
        if prefix == "DEADLOCK_LOCK":
            if saw_contention:
                first_violation = _fail(i, "deadlock_after_contention_block", observed_prefix=prefix)
                break
            if prev_deadlock is not None and not (addr > prev_deadlock):
                first_violation = _fail(i, "deadlock_lock_not_strictly_ascending", prev=prev_deadlock, observed=addr)
                break
            prev_deadlock = addr
        elif prefix == "CONTENTION_LOCK":
            saw_contention = True
            if prev_contention is not None and not (addr > prev_contention):
                first_violation = _fail(i, "contention_lock_not_strictly_ascending", prev=prev_contention, observed=addr)
                break
            prev_contention = addr
        else:
            first_violation = _fail(i, "unexpected_prefix_in_lock_block", observed_prefix=prefix)
            break
    return first_violation is None, {"row_count": len(lines), "first_violation": first_violation}


def d5_solve_script_shortcut_scan():
    if not SOLVE_SCRIPT_PATH.is_file():
        return False, {"reason": "solve_script_missing", "path": str(SOLVE_SCRIPT_PATH)}
    script_bytes = SOLVE_SCRIPT_PATH.read_bytes()
    hits = []
    for regex, label in FORBIDDEN_SOLVE_PATTERNS_BYTES:
        m = regex.search(script_bytes)
        if m:
            hits.append({"pattern": label, "byte_offset": m.start(), "matched_bytes": m.group().decode("utf-8", errors="replace")})
    return len(hits) == 0, {"hits": hits}


def d6_solve_script_line_budget():
    if not SOLVE_SCRIPT_PATH.is_file():
        return False, {"reason": "solve_script_missing", "path": str(SOLVE_SCRIPT_PATH)}
    data = SOLVE_SCRIPT_PATH.read_bytes()
    newlines = data.count(b"\n")
    tail = 0 if data.endswith(b"\n") else 1
    line_count = newlines + tail
    ok = line_count <= SOLVE_SCRIPT_LINE_BUDGET
    return ok, {"line_count": line_count, "budget": SOLVE_SCRIPT_LINE_BUDGET}


REASON_MAP = {
    "D1": "D1_output_file_missing_or_empty_or_invalid_utf8",
    "D2": "D2_row_shape_invariant_violation",
    "D3": "D3_output_line_set_mismatch_with_reference",
    "D4": "D4_row_ordering_violation",
    "D5": "D5_solve_script_matches_bound_shortcut_pattern",
    "D6": "D6_solve_script_line_count_exceeds_budget",
}


def main():
    breakdown = {}

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

    all_pass = all([ok_d1, ok_d2, ok_d3, ok_d4, ok_d5, ok_d6])
    if all_pass:
        reason = "all_deliverables_passed"
    else:
        for key, label in (("D1_output_exists", "D1"), ("D2_row_shape_invariant", "D2"),
                           ("D3_set_equality", "D3"), ("D4_row_ordering", "D4"),
                           ("D5_solve_script_shortcut_scan", "D5"), ("D6_solve_script_line_budget", "D6")):
            if not breakdown[key]["pass"]:
                reason = REASON_MAP[label]
                break
        else:
            reason = "unknown_failure"

    _reward(all_pass, reason, breakdown)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
