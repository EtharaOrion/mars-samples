"""Grader for cargo-audit-triage.

Runs D1 through D6 against the agent output at /workspace/out/triage.tsv
and writes the reward JSON to /logs/verifier/reward.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("CARGO_AUDIT_OUTPUT", "/workspace/out/triage.tsv"))
SOLVE_SCRIPT_PATH = Path(os.environ.get("CARGO_AUDIT_SOLVE_SCRIPT", "/workspace/solve.sh"))
REWARD_PATH = Path(os.environ.get("REWARD_PATH", "/logs/verifier/reward.json"))

SOLVE_SCRIPT_LINE_BUDGET = 90

SEVERITY_REGEX  = re.compile(r"^(CRITICAL|HIGH|MEDIUM)$")
ADV_ID_REGEX    = re.compile(r"^RUSTSEC-[0-9]{4}-[0-9]{4}$")
JOIN_KEY_REGEX  = re.compile(r"^[a-z0-9][a-z0-9_-]*:(direct|transitive):[a-z0-9][a-z0-9_-]*$")

SEVERITY_RANK = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1}

FORBIDDEN_SOLVE_PATTERNS_BYTES = [
    (re.compile(rb"FORGE_HOLDOUT_CANARY_[A-Z0-9]{32}"),        "canary_token"),
    (re.compile(rb"solution/grounding\.yaml"),                "grounding_yaml_path"),
    (re.compile(rb"solution/TRUTH\.md"),                      "truth_md_path"),
    (re.compile(rb"dataset/[0-9a-f-]{36}/(solution|tests)/"),  "dataset_holdout_path"),
    (re.compile(rb"/holdout/"),                                "holdout_slash"),
    (re.compile(rb"HARDCODED_TRIAGE_RECITAL_BEGIN"),           "hardcoded_recital_begin"),
    (re.compile(rb"HARDCODED_TRIAGE_RECITAL_END"),             "hardcoded_recital_end"),
    (re.compile(rb"reference_row_set"),                        "grounding_key_reference_row_set"),
    (re.compile(rb"reference_advisory_id_set"),                "grounding_key_reference_advisory_id_set"),
    (re.compile(rb"reference_join_key_set"),                   "grounding_key_reference_join_key_set"),
    (re.compile(rb"reference_severity_bucket_set"),            "grounding_key_reference_severity_bucket_set"),
    (re.compile(rb"canonical_output_form"),                    "grounding_key_canonical_output_form"),
    (re.compile(rb"per_field_schema_shape_regex_family"),      "grounding_key_per_field_schema"),
    (re.compile(rb"row_ordering_comparator_contract"),         "grounding_key_row_ordering_comparator"),
    (re.compile(rb"(^|[^_a-zA-Z])date\s+(-d\s+|-I|-u\s|\+%)"), "wall_clock_date_family"),
    (re.compile(rb"\bdatetime\.now\s*\("),                  "wall_clock_datetime_now"),
    (re.compile(rb"\bdatetime\.today\s*\("),                "wall_clock_datetime_today"),
    (re.compile(rb"\bdate\.today\s*\("),                    "wall_clock_date_today"),
    (re.compile(rb"\btime\.time\s*\("),                     "wall_clock_time_time"),
    (re.compile(rb"\btime\.localtime\s*\("),                "wall_clock_time_localtime"),
    (re.compile(rb"\btime\.gmtime\s*\("),                   "wall_clock_time_gmtime"),
    (re.compile(rb"\bcargo\s+(update|publish|yank|install|search|owner|login)\b"), "cargo_mutation"),
    (re.compile(rb"\bcargo\s+audit\s+fetch\b"),             "cargo_audit_fetch"),
    (re.compile(rb"\bcurl\b"),                                "network_curl"),
    (re.compile(rb"\bwget\b"),                                "network_wget"),
    (re.compile(rb"\bgit\s+clone\b"),                        "network_git_clone"),
    (re.compile(rb"/tests/grader\.py"),                         "grader_source_path_reference"),
    (re.compile(rb"EXPECTED_LINES"),                              "expected_lines_symbol_reference"),
    (re.compile(rb"EXPECTED_TSV_SHA256"),                         "expected_hash_symbol_reference"),
    (re.compile(rb"from\s+grader\s+import"),                    "grader_module_from_import"),
    (re.compile(rb"sys\.path\.insert\s*\([^)]*['\"]/?tests"), "tests_dir_syspath_insert"),
    (re.compile(rb"sys\.path\.append\s*\([^)]*['\"]/?tests"), "tests_dir_syspath_append"),
    (re.compile(rb"import\s+importlib.*\.import_module\s*\(['\"]grader"), "grader_importlib_dynamic_import"),
]


EXPECTED_TSV_SHA256 = "b8618aa3e18567caa3386a44ac8c35c939f93566af6eeedab03c4b5e86c28cfb"


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
        if len(parts) != 3:
            first_violation = {"row_index": i, "reason": "wrong_field_count", "observed_field_count": len(parts), "observed_line": line[:200]}
            break
        f1, f2, f3 = parts
        if not f1 or not f2 or not f3:
            first_violation = {"row_index": i, "reason": "empty_field", "observed_line": line[:200]}
            break
        if not SEVERITY_REGEX.match(f1):
            first_violation = {"row_index": i, "field_index": 1, "reason": "severity_bucket_regex_mismatch", "observed_value": f1[:200]}
            break
        if not ADV_ID_REGEX.match(f2):
            first_violation = {"row_index": i, "field_index": 2, "reason": "advisory_id_regex_mismatch", "observed_value": f2[:200]}
            break
        if not JOIN_KEY_REGEX.match(f3):
            first_violation = {"row_index": i, "field_index": 3, "reason": "join_key_regex_mismatch", "observed_value": f3[:200]}
            break
    return first_violation is None, {"row_count": len(lines), "first_violation": first_violation}


def d3_set_equality(actual_bytes):
    text = actual_bytes.decode("utf-8", errors="replace")
    actual_lines = [ln for ln in text.split("\n") if ln != ""]
    canonical_bytes = ("\n".join(sorted(actual_lines)) + "\n").encode("utf-8")
    actual_hash = hashlib.sha256(canonical_bytes).hexdigest()
    ok = (actual_hash == EXPECTED_TSV_SHA256)
    return ok, {
        "actual_count": len(actual_lines),
        "actual_canonical_sha256": actual_hash,
        "expected_canonical_sha256": EXPECTED_TSV_SHA256,
    }


def d4_row_ordering(actual_bytes):
    text = actual_bytes.decode("utf-8", errors="replace")
    lines = [ln for ln in text.split("\n") if ln != ""]
    first_violation = None
    prev_rank = None
    prev_adv = None
    prev_jk = None
    for i, line in enumerate(lines, start=1):
        parts = line.split("\t")
        if len(parts) != 3:
            first_violation = {"position_index": i, "reason": "wrong_field_count", "observed_parts": parts[:1]}
            break
        sev, adv, jk = parts
        rank = SEVERITY_RANK.get(sev)
        if rank is None:
            first_violation = {"position_index": i, "reason": "unknown_severity_bucket", "observed": sev}
            break
        if prev_rank is not None:
            if rank > prev_rank:
                first_violation = {"position_index": i, "reason": "severity_rank_ascended",
                                   "prev_rank": prev_rank, "observed_rank": rank}
                break
            if rank == prev_rank:
                if adv < prev_adv:
                    first_violation = {"position_index": i, "reason": "advisory_id_descended_within_bucket",
                                       "prev": prev_adv, "observed": adv}
                    break
                if adv == prev_adv and jk <= prev_jk:
                    first_violation = {"position_index": i, "reason": "join_key_not_strictly_ascending_within_adv",
                                       "prev": prev_jk, "observed": jk}
                    break
        prev_rank, prev_adv, prev_jk = rank, adv, jk
    return first_violation is None, {"row_count": len(lines), "first_violation": first_violation}


def d5_solve_script_shortcut_scan():
    if not SOLVE_SCRIPT_PATH.is_file():
        return False, {"reason": "solve_script_missing", "path": str(SOLVE_SCRIPT_PATH)}
    script_bytes = SOLVE_SCRIPT_PATH.read_bytes()
    hits = []
    for regex, label in FORBIDDEN_SOLVE_PATTERNS_BYTES:
        m = regex.search(script_bytes)
        if m:
            hits.append({"pattern": label, "byte_offset": m.start(),
                         "matched_bytes": m.group().decode("utf-8", errors="replace")})
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
