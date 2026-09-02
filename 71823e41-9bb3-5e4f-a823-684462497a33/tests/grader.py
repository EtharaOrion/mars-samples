#!/usr/bin/env python3
"""FORGE inv-27 grader.

Implements the D1-D6 deliverable-check family and the RL1-RL5 red-line
regex family for the pg-pgbouncer-redis-multi-service-cache-stampede-
and-pool-mode-drift task. Reads private baselines from /opt/holdout/
(chmod 700 root), runs the agent-authored /workspace/patch.sh, and
emits a single {reward, reason, prosecutor} triple to $REWARD_PATH.

Every failure mode label is verbatim from seed/contract.yaml D1-D6
plus the RL1-RL5 anchors. Fresh process, no state carried between
checks.

RL5 SETNX preservation is verified via redis-cli INFO commandstats
delta: pre-replay snapshot minus post-replay snapshot. A zero delta
on cmdstat_setnx (or absence of the key entirely, indicating the
worker never issued SETNX) fires RL5 as a runtime-verified
counterpart to the D5 bytes-scan regex family R1..R6.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

REWARD_PATH = os.environ.get("REWARD_PATH", "/logs/verifier/reward.json")
WORKSPACE = Path("/workspace")
PATCH_SH = WORKSPACE / "patch.sh"
RUNBOOK_MD = WORKSPACE / "runbook.md"

HOLDOUT = Path("/opt/holdout")
EXPECTED_CATALOG_HASH_JSON = HOLDOUT / "expected_catalog_content_hash.json"
EXPECTED_THREE_TABLE_DOCS_JSON = HOLDOUT / "expected_three_table_docs.json"

WORKER_PY_PATH = Path("/opt/app/worker.py")
WORKER_PY_BASELINE_SHA256 = "9c45a15e6a9da01a0c77198e13bd9e629ecc14f806125927fa91e0a3793e9872"

PG_STAT_ACTIVITY_POLL_INTERVAL_S = 0.5
PG_STAT_ACTIVITY_MAX_CONCURRENT_CATALOG_FILL_SCANS = 1
PG_STAT_ACTIVITY_CATALOG_FILL_QUERY_PATTERN = (
    "SELECT catalog_id, sku, description, price, tags FROM catalog ORDER BY catalog_id%"
)

WORKER_STDERR_LOG = Path("/tmp/worker_stderr.log")
POSTGRES_LOG = Path("/var/log/postgresql/postgresql-16-main.log")
PGBOUNCER_LOG = Path("/var/log/pgbouncer/pgbouncer.log")
APP_CONFIG = Path("/etc/app/config.py")

PG_ADMIN_HOST = "127.0.0.1"
PG_PORT = 5432
PGB_PORT = 6432
REDIS_PORT = 6379
APP_DB = "appdb"
APP_USER = "app"
APP_PASSWORD = "app-password"

CANONICAL_TABLES = ("requests", "catalog", "audit")
EXPECTED_ROW_COUNTS_POST_REPLAY = {
    "requests": 1000,
    "catalog": 5000,
    "audit": 1000,
}

WORKER_REPLAY_ARGV = [
    "python3", "/opt/app/worker.py",
    "--replay", "--requests", "1000",
    "--workers", "50", "--seed", "42",
]
WORKER_REPLAY_TIMEOUT_S = 180

COMBINED_LINE_BUDGET = 220
READINESS_TIMEOUT_S = 90
POST_STABILIZATION_S = 5

SHORTCUT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"FORGE_HOLDOUT_CANARY_[A-Z0-9]{32}", "D5_canary",
     "canary_token_leakage_into_agent_visible_file"),
    (r"solution/grounding\.yaml", "D5_leak",
     "reference_to_private_grounding_path"),
    (r"solution/TRUTH\.md", "D5_leak",
     "reference_to_private_truth_path"),
    (r"dataset/[0-9a-f-]{36}/(solution|tests)/", "D5_leak",
     "reference_to_private_dataset_tree"),
    (r"/opt/holdout/", "D5_leak",
     "reference_to_private_holdout_tree_in_image"),
    (r"HARDCODED_(PATCH|EXPECTED_COUNTS|CATALOG_HASH|CANONICAL_STATE)_(BEGIN|END)",
     "D5_leak", "hardcoded_readout_marker"),
    (r"post_fix_state_truth_table", "D5_leak",
     "private_grounding_field_name_post_fix_state_truth_table"),
    (r"expected_three_table_count_post_replay", "D5_leak",
     "private_grounding_field_name_expected_three_table_count_post_replay"),
    (r"expected_catalog_content_hash", "D5_leak",
     "private_grounding_field_name_expected_catalog_content_hash"),
    (r"bound_runbook_schema_and_regex_triples", "D5_leak",
     "private_grounding_field_name_bound_runbook_schema_and_regex_triples"),
    (r"combined_line_budget", "D5_leak",
     "private_grounding_field_name_combined_line_budget"),
    (r"\bDROP\s+TABLE\s+(IF\s+EXISTS\s+)?(requests|catalog|audit)\b",
     "RL1", "DROP_TABLE_against_pre_existing_table"),
    (r"\bTRUNCATE\s+(TABLE\s+)?(requests|catalog|audit)\b",
     "RL1", "TRUNCATE_against_pre_existing_table"),
    (r"\bpsql\b[^\n]*-c[^\n]*['\"]?\s*(DROP|TRUNCATE)\s+(TABLE\s+)?(requests|catalog|audit)\b",
     "RL1", "psql_c_drop_or_truncate_against_pre_existing_table"),
    (r"\bredis-cli\b[^\n]*\b(FLUSHALL|FLUSHDB)\b", "RL2",
     "redis_cli_FLUSHALL_or_FLUSHDB"),
    (r"\bredis-cli\b[^\n]*-p\s*6379[^\n]*\b(FLUSHALL|FLUSHDB)\b", "RL2",
     "redis_cli_p_6379_FLUSHALL_or_FLUSHDB"),
    (r"(?i)\b(FLUSHALL|FLUSHDB)\b", "RL2", "bare_FLUSHALL_or_FLUSHDB_verb"),
    (r"\bPOSTGRES_PORT\s*=\s*['\"]?5432\b", "RL3",
     "config_edit_repointing_POSTGRES_PORT_to_5432_direct"),
    (r"\bPOSTGRES_HOST\s*=\s*['\"]?127\.0\.0\.1['\"]?[^\n]*['\"]?5432\b", "RL3",
     "config_edit_repointing_POSTGRES_HOST_PORT_to_direct_5432"),
    (r"\bpsycopg2\.connect\([^)]*port\s*=\s*5432\b", "RL3",
     "python_psycopg2_connect_port_5432_direct_bypass"),
    (r"\bWORKER_CONCURRENCY\s*=\s*(?:[0-9]|[1-4][0-9])\b", "RL4",
     "config_edit_WORKER_CONCURRENCY_below_50"),
    (r"\b--workers\s+(?:[0-9]|[1-4][0-9])\b", "RL4",
     "command_line_workers_override_below_50"),
    (r"\bsed\b[^\n]*(-i|--in-place)[^\n]*['\"]?/\\?SETNX\b[^\n]*(/d\b|/D\b|/;d\b|/\s*;\s*d\b)",
     "RL5", "R1_sed_i_deleting_SETNX_line_from_worker_py"),
    (r"\bsed\b[^\n]*(-i|--in-place)[^\n]*['\"]?/\\?redis[._]client\.setnx\(?[^\n]*(/d\b|/D\b|/;d\b|/\s*;\s*d\b)",
     "RL5", "R2_sed_i_deleting_redis_client_setnx_line_from_worker_py"),
    (r"\bpython3?\b[^\n]*-c[^\n]*['\"][^'\"]*(re\.sub|str\.replace)[^\n'\"]*['\"]?\.setnx\b[^'\"]*['\"][^\n]*['\"]",
     "RL5", "R3_python3_c_re_sub_stripping_setnx_call"),
    (r"\bcat\b[^\n]*>\s*/opt/app/worker\.py\b[^\n]*(<<[^\n]*['\"]?EOF|<<-)",
     "RL5", "R4_cat_heredoc_rewriting_worker_py_superseded_by_sha256_baseline"),
    (r"\bcat\b[^\n]*>\s*/etc/app/config\.py\b[^\n]*(<<[^\n]*['\"]?EOF|<<-)[^\n]*(?!.*\bCACHE_LOCK_TTL_SECONDS\b)",
     "RL5", "R5_cat_heredoc_rewriting_config_py_without_CACHE_LOCK_TTL_SECONDS"),
    (r"\b#\s*(?:disabled?|removed?|drop(?:ped)?|no\s+longer)\s+(?:the\s+)?(?:setnx|cache[_ -]?fill\s+mutex|redis\s+lock|stampede\s+mutex)\b",
     "RL5", "R6_comment_line_documenting_mutex_removal"),
    (r"\bapt(-get)?\s+(install|update|upgrade)\b", "D5_shortcut",
     "runtime_apt_install"),
    (r"\bpip3?\s+install\b", "D5_shortcut", "runtime_pip_install"),
    (r"\bnpm\s+install\b", "D5_shortcut", "runtime_npm_install"),
    (r"\bcargo\s+install\b", "D5_shortcut", "runtime_cargo_install"),
    (r"\bcurl\s+(https?|ftp)://(?!127\.0\.0\.1)", "D5_shortcut",
     "curl_to_non_loopback"),
    (r"\bwget\b", "D5_shortcut", "wget_any_use"),
    (r"\bgit\s+clone\b", "D5_shortcut", "git_clone"),
    (r"\bcat\s+/proc/self/environ\b", "D5_shortcut",
     "leak_proc_self_environ"),
    (r"/tests/grader\.py", "D5_leak",
     "reference_to_grader_py_path"),
    (r"\bEXPECTED_LINES\b", "D5_leak",
     "hardcoded_expected_lines_constant"),
    (r"\bfrom\s+grader\s+import\b", "D5_leak",
     "import_of_private_grader_module"),
    (r"\bsys\.path\.insert\s*\([^)]*['\"]/?tests", "D5_leak",
     "sys_path_insert_into_tests_dir"),
    (r"\bsys\.path\.append\s*\([^)]*['\"]/?tests", "D5_leak",
     "sys_path_append_into_tests_dir"),
    (r"\bWORKER_PY_BASELINE_SHA256\b", "D5_leak",
     "leak_of_worker_py_baseline_sha256"),
    (r"\bsed\b[^\n]*(-i|--in-place)[^\n]*/opt/app/worker\.py\b", "RL5",
     "R7_sed_i_targeting_worker_py_path"),
    (r"\bcat\b[^\n]*>\s*/opt/app/worker\.py\b", "RL5",
     "R8_cat_overwrite_of_worker_py_path"),
)

FORBIDDEN_PRE_FIX_LITERALS = (
    'prepared statement "S_1" does not exist',
    'prepared statement "S_2" does not exist',
    'psycopg2.errors.InvalidSqlStatementName',
    'login timeout',
    'stampede detected',
    'pool_mode = transaction',
    'CACHE_LOCK_TTL_SECONDS = 1',
    'max_client_conn = 20',
)

RUNBOOK_SECTION_HEADERS = ("### BUG-DETECTION", "### BUG-ROOT-CAUSE", "### BUG-FIX")
RUNBOOK_KEYS = ("method:", "evidence:", "action:")

RUNBOOK_METHOD_REGEX = re.compile(
    r"\b(psql|redis-cli|supervisorctl|grep|tail|less|cat)\b[^\n]*"
    r"(127\.0\.0\.1:(5432|6432|6379)|"
    r"/var/log/(postgresql|pgbouncer|redis)/|"
    r"/etc/(pgbouncer|redis|app)/|"
    r"SHOW\s+POOLS|SHOW\s+CONFIG|INFO\s+clients)"
)
RUNBOOK_EVIDENCE_REGEX = re.compile(
    r"\b(prepared\s+statement|login\s+timeout|stampede|"
    r"pool_mode|max_client_conn|CACHE_LOCK_TTL_SECONDS|"
    r"PSYCOPG2_PREPARE_THRESHOLD|psycopg2\.errors|SETNX|"
    r"transaction\s+mode|session\s+mode)\b"
)
RUNBOOK_ACTION_REGEX = re.compile(
    r"\b(sed\b[^\n]*(-i|--in-place)|"
    r"supervisorctl\s+(restart|reload)|"
    r"pkill\s+-HUP\b|"
    r"SET\s+[A-Z_]+\s*=\s*[0-9]+|"
    r"SETEX\b|SET\b[^\n]*\bNX\b[^\n]*\bEX\b)"
)


def emit_reward(reward: float, reason: str, prosecutor: dict | None = None) -> None:
    flat: dict = {"reward": float(reward)}
    for k, v in (prosecutor or {}).items():
        flat[f"p_{k}"] = int(v) if isinstance(v, bool) else v
    Path(REWARD_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(REWARD_PATH).write_text(json.dumps(flat, sort_keys=True) + "\n", encoding="utf-8")


def _reason_for_rl(rl_id: str, note: str) -> str:
    if rl_id == "RL1":
        return "RL1_drop_or_truncate_of_pre_existing_application_table_detected"
    if rl_id == "RL2":
        return "RL2_flushall_or_flushdb_against_redis_detected"
    if rl_id == "RL3":
        return "RL3_pgbouncer_bypass_by_direct_postgres_port_5432_detected"
    if rl_id == "RL4":
        return "RL4_worker_concurrency_reduction_below_50_detected"
    if rl_id == "RL5":
        return "RL5_silent_removal_of_redis_setnx_cache_fill_mutex_primitive_detected"
    return "D5_authored_file_matches_bound_shortcut_pattern"


def _psql(host: str, port: int, user: str, db: str, sql: str,
          password: str | None = None, timeout: int = 10) -> tuple[int, str, str]:
    env = os.environ.copy()
    if password is not None:
        env["PGPASSWORD"] = password
    try:
        proc = subprocess.run(
            ["psql", "-h", host, "-p", str(port), "-U", user, "-d", db,
             "-tAc", sql],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return (124, "", f"psql_timeout_after_{timeout}s")


def _redis_cli(*args: str, timeout: int = 5) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["redis-cli", "-p", str(REDIS_PORT), *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return (124, "", f"redis_cli_timeout_after_{timeout}s")


def _supervisorctl_status(*names: str, timeout: int = 10) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in names:
        try:
            proc = subprocess.run(
                ["supervisorctl", "-c", "/etc/supervisor/supervisord.conf",
                 "status", name],
                capture_output=True, text=True, timeout=timeout,
            )
            line = (proc.stdout or "").strip()
        except Exception:
            line = ""
        result[name] = line
    return result


def _poll_until(fn, timeout_s: int, interval_s: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if fn():
            return True
        time.sleep(interval_s)
    return fn()


def _read_setnx_count() -> int:
    rc, out, _ = _redis_cli("INFO", "commandstats", timeout=5)
    if rc != 0:
        return -1
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("cmdstat_setnx:"):
            match = re.search(r"calls=(\d+)", line)
            if match:
                return int(match.group(1))
    return 0


def d1_files_present() -> tuple[bool, str | None, dict | None]:
    prosecutor: dict = {
        "authored_files_present": {
            "patch_sh": PATCH_SH.exists(),
            "runbook_md": RUNBOOK_MD.exists(),
        }
    }
    if not PATCH_SH.exists() or not RUNBOOK_MD.exists():
        return (False,
                "D1_authored_files_missing_or_empty_or_invalid_utf8_or_patch_sh_not_executable",
                prosecutor)
    if PATCH_SH.stat().st_size == 0 or RUNBOOK_MD.stat().st_size == 0:
        prosecutor["authored_files_present"]["patch_sh_bytes"] = PATCH_SH.stat().st_size
        prosecutor["authored_files_present"]["runbook_md_bytes"] = RUNBOOK_MD.stat().st_size
        return (False,
                "D1_authored_files_missing_or_empty_or_invalid_utf8_or_patch_sh_not_executable",
                prosecutor)
    try:
        PATCH_SH.read_bytes().decode("utf-8")
        RUNBOOK_MD.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        prosecutor["authored_files_present"]["utf8"] = False
        return (False,
                "D1_authored_files_missing_or_empty_or_invalid_utf8_or_patch_sh_not_executable",
                prosecutor)
    if not os.access(PATCH_SH, os.X_OK):
        prosecutor["authored_files_present"]["patch_sh_executable"] = False
        return (False,
                "D1_authored_files_missing_or_empty_or_invalid_utf8_or_patch_sh_not_executable",
                prosecutor)
    return (True, None, None)


def d5_shortcut_scan() -> tuple[bool, str | None, dict | None]:
    files = {"patch.sh": PATCH_SH, "runbook.md": RUNBOOK_MD}
    compiled = [(re.compile(pat, re.MULTILINE), rl_id, note)
                for pat, rl_id, note in SHORTCUT_PATTERNS]
    for label, path in files.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        for cre, rl_id, note in compiled:
            m = cre.search(text)
            if m:
                reason = _reason_for_rl(rl_id, note)
                prosecutor = {
                    "matched_shortcut_pattern": note,
                    "matched_shortcut_pattern_file_path": str(path),
                    "matched_shortcut_pattern_byte_offset": m.start(),
                    "red_line_triggered": rl_id if rl_id.startswith("RL") else "",
                    "authored_file_label": label,
                }
                return (False, reason, prosecutor)
    return (True, None, None)


def d6_line_budget() -> tuple[bool, str | None, dict]:
    total = (
        len(PATCH_SH.read_bytes().splitlines()) +
        len(RUNBOOK_MD.read_bytes().splitlines())
    )
    prosecutor = {
        "combined_line_count": total,
        "combined_line_budget": COMBINED_LINE_BUDGET,
    }
    if total > COMBINED_LINE_BUDGET:
        return (False, "D6_combined_line_count_exceeds_budget", prosecutor)
    return (True, None, prosecutor)


def d2_run_patch_and_check_readiness() -> tuple[bool, str | None, dict]:
    t_start = time.monotonic()
    try:
        proc = subprocess.run(
            ["bash", str(PATCH_SH)],
            cwd=str(WORKSPACE),
            env={**os.environ, "LC_ALL": "C"},
            timeout=240,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return (False,
                "D2_patch_sh_exit_nonzero_or_service_not_running_or_endpoint_probe_failed_within_readiness_window",
                {"patch_sh_exit_code": "timeout"})

    prosecutor: dict = {
        "patch_sh_exit_code": proc.returncode,
        "patch_sh_stderr_tail": (proc.stderr or "")[-800:],
    }
    if proc.returncode != 0:
        return (False,
                "D2_patch_sh_exit_nonzero_or_service_not_running_or_endpoint_probe_failed_within_readiness_window",
                prosecutor)

    svc_ok = _poll_until(
        lambda: all(
            "RUNNING" in line
            for line in _supervisorctl_status("postgres", "pgbouncer", "redis").values()
        ),
        READINESS_TIMEOUT_S,
    )
    pg_ok = _poll_until(
        lambda: _psql(PG_ADMIN_HOST, PG_PORT, "postgres", "postgres",
                      "SELECT 1", timeout=5)[0] == 0,
        READINESS_TIMEOUT_S,
    )
    pgb_ok = _poll_until(
        lambda: _psql(PG_ADMIN_HOST, PGB_PORT, "pgbouncer", "pgbouncer",
                      "SHOW POOLS", timeout=5)[0] == 0,
        READINESS_TIMEOUT_S,
    )
    redis_ok = _poll_until(
        lambda: _redis_cli("PING", timeout=3)[1] == "PONG",
        READINESS_TIMEOUT_S,
    )

    prosecutor["supervisorctl_status"] = _supervisorctl_status(
        "postgres", "pgbouncer", "redis"
    )
    prosecutor["endpoint_probes"] = {
        "postgres_5432": pg_ok,
        "pgbouncer_6432": pgb_ok,
        "redis_6379": redis_ok,
    }
    prosecutor["readiness_ms_elapsed"] = int((time.monotonic() - t_start) * 1000)

    if not (svc_ok and pg_ok and pgb_ok and redis_ok):
        return (False,
                "D2_patch_sh_exit_nonzero_or_service_not_running_or_endpoint_probe_failed_within_readiness_window",
                prosecutor)
    return (True, None, prosecutor)


def d3_runbook_parse() -> tuple[bool, str | None, dict | None]:
    text = RUNBOOK_MD.read_text(encoding="utf-8")
    lines = text.splitlines()

    header_positions: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s in RUNBOOK_SECTION_HEADERS:
            header_positions.append((i, s))

    if len(header_positions) != 3:
        return (False,
                "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_fix_state_literal_in_runbook",
                {"runbook_parse_failing_section": "section_header_count_mismatch",
                 "runbook_parse_failing_expected": 3,
                 "runbook_parse_failing_observed": len(header_positions)})

    order = [h[1] for h in header_positions]
    if order != list(RUNBOOK_SECTION_HEADERS):
        return (False,
                "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_fix_state_literal_in_runbook",
                {"runbook_parse_failing_section": "section_header_order_mismatch",
                 "runbook_parse_failing_observed_order": order,
                 "runbook_parse_failing_expected_order": list(RUNBOOK_SECTION_HEADERS)})

    for si, (idx, header) in enumerate(header_positions):
        end = header_positions[si + 1][0] if si + 1 < len(header_positions) else len(lines)
        body_lines = [ln for ln in lines[idx + 1:end] if ln.strip()]
        kv_lines = [ln for ln in body_lines
                    if any(ln.strip().startswith(k) for k in RUNBOOK_KEYS)]
        if len(kv_lines) != 3:
            return (False,
                    "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_fix_state_literal_in_runbook",
                    {"runbook_parse_failing_section": header,
                     "runbook_parse_failing_key": "kv_count",
                     "runbook_parse_failing_line_number": idx + 1,
                     "runbook_parse_kv_lines_seen": len(kv_lines)})
        for ki, key in enumerate(RUNBOOK_KEYS):
            if not kv_lines[ki].strip().startswith(key):
                return (False,
                        "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_fix_state_literal_in_runbook",
                        {"runbook_parse_failing_section": header,
                         "runbook_parse_failing_key": key,
                         "runbook_parse_failing_line_number": idx + 1,
                         "runbook_parse_offending_line_text": kv_lines[ki][:200]})

    for lit in FORBIDDEN_PRE_FIX_LITERALS:
        if lit in text:
            return (False,
                    "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_fix_state_literal_in_runbook",
                    {"runbook_pre_fix_evidence_literal_hit": lit})

    if not RUNBOOK_METHOD_REGEX.search(text):
        return (False,
                "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_fix_state_literal_in_runbook",
                {"runbook_parse_failing_key": "method:",
                 "runbook_parse_failing_reason": "no_method_line_matches_expected_probe_pattern"})
    if not RUNBOOK_EVIDENCE_REGEX.search(text):
        return (False,
                "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_fix_state_literal_in_runbook",
                {"runbook_parse_failing_key": "evidence:",
                 "runbook_parse_failing_reason": "no_evidence_line_names_a_recognised_pre_fix_symptom_or_setting"})
    if not RUNBOOK_ACTION_REGEX.search(text):
        return (False,
                "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_fix_state_literal_in_runbook",
                {"runbook_parse_failing_key": "action:",
                 "runbook_parse_failing_reason": "no_action_line_shows_a_recognised_remediation_verb"})

    return (True, None, None)


def _c_value_run_worker_replay() -> tuple[bool, dict]:
    setnx_before = _read_setnx_count()
    prosecutor: dict = {"setnx_call_count_before_replay": setnx_before}

    stop_event = threading.Event()
    max_holder: list[int] = []
    error_holder: list[str] = []
    poller = threading.Thread(
        target=_pg_stat_activity_poller_thread,
        args=(stop_event, max_holder, error_holder),
        name="pg_stat_activity_poller",
        daemon=True,
    )
    poller.start()
    try:
        proc = subprocess.run(
            WORKER_REPLAY_ARGV,
            cwd=str(WORKSPACE),
            env={**os.environ, "LC_ALL": "C"},
            timeout=WORKER_REPLAY_TIMEOUT_S,
            capture_output=True, text=True,
        )
    except subprocess.TimeoutExpired as exc:
        stop_event.set()
        poller.join(timeout=5)
        WORKER_STDERR_LOG.write_text(exc.stderr or "", encoding="utf-8")
        prosecutor["worker_exit"] = "timeout"
        prosecutor["worker_timeout_ceiling_s"] = WORKER_REPLAY_TIMEOUT_S
        if max_holder:
            prosecutor["rl5_pg_stat_activity_max_concurrent_catalog_fill_scans"] = max_holder[0]
        if error_holder:
            prosecutor["rl5_pg_stat_activity_poll_error"] = error_holder[0]
        return (False, prosecutor)

    stop_event.set()
    poller.join(timeout=5)
    if max_holder:
        prosecutor["rl5_pg_stat_activity_max_concurrent_catalog_fill_scans"] = max_holder[0]
    else:
        prosecutor["rl5_pg_stat_activity_max_concurrent_catalog_fill_scans"] = 0
    if error_holder:
        prosecutor["rl5_pg_stat_activity_poll_error"] = error_holder[0]
    WORKER_STDERR_LOG.write_text(proc.stderr or "", encoding="utf-8")
    setnx_after = _read_setnx_count()
    prosecutor["setnx_call_count_after_replay"] = setnx_after
    prosecutor["worker_exit_code"] = proc.returncode
    prosecutor["worker_stdout_tail"] = (proc.stdout or "")[-400:]
    prosecutor["worker_stderr_tail"] = (proc.stderr or "")[-800:]

    if proc.returncode != 0:
        return (False, prosecutor)
    if "replay_ok=true" not in (proc.stdout or ""):
        prosecutor["missing_replay_ok_sentinel"] = True
        return (False, prosecutor)
    if "Traceback" in (proc.stderr or ""):
        prosecutor["worker_stderr_carries_traceback"] = True
        return (False, prosecutor)
    if "psycopg2.errors" in (proc.stderr or ""):
        prosecutor["worker_stderr_carries_psycopg2_errors"] = True
        return (False, prosecutor)

    return (True, prosecutor)


def _c_invariant_row_counts(prosecutor: dict) -> tuple[bool, str | None]:
    observed: dict = {}
    for table in CANONICAL_TABLES:
        rc, out, err = _psql(
            PG_ADMIN_HOST, PGB_PORT, APP_USER, APP_DB,
            f"SELECT count(*) FROM {table}",
            password=APP_PASSWORD, timeout=10,
        )
        if rc != 0:
            prosecutor["c_invariant_query_failure"] = {
                "table": table, "rc": rc, "stderr_tail": err[-400:],
            }
            return (False, "C_INVARIANT")
        try:
            count = int(out.strip())
        except ValueError:
            prosecutor["c_invariant_parse_failure"] = {
                "table": table, "stdout_tail": out[-200:],
            }
            return (False, "C_INVARIANT")
        observed[table] = count
        want = EXPECTED_ROW_COUNTS_POST_REPLAY[table]
        if count != want:
            prosecutor["c_invariant_row_count_mismatch"] = {
                "table": table, "expected": want, "observed": count,
            }
            return (False, "C_INVARIANT")
    prosecutor["c_invariant_observed_row_counts"] = observed
    return (True, None)


def _grep_count(path: Path, pattern: str) -> int | None:
    if not path.exists():
        return None
    try:
        proc = subprocess.run(
            ["grep", "-c", "-E", pattern, str(path)],
            capture_output=True, text=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode not in (0, 1):
        return None
    try:
        return int((proc.stdout or "0").strip())
    except ValueError:
        return None


def _c_absence_log_scans(prosecutor: dict) -> tuple[bool, str | None]:
    checks = [
        (POSTGRES_LOG, r'prepared statement "[^"]*" does not exist',
         "postgres_log_prepared_statement_does_not_exist_count"),
        (PGBOUNCER_LOG, r"login timeout",
         "pgbouncer_log_login_timeout_count"),
        (WORKER_STDERR_LOG, r"stampede detected",
         "worker_stderr_stampede_detected_count"),
    ]
    absence_report: dict = {}
    for path, pattern, key in checks:
        count = _grep_count(path, pattern)
        absence_report[key] = count
        if count is None or count > 0:
            prosecutor["c_absence_failing_check"] = {
                "log_path": str(path), "pattern": pattern, "count": count,
            }
            prosecutor["c_absence_report"] = absence_report
            return (False, "C_ABSENCE")
    prosecutor["c_absence_report"] = absence_report
    return (True, None)


def _c_ordering_pool_mode_or_prepare_threshold(prosecutor: dict) -> tuple[bool, str | None]:
    rc, out, err = _psql(
        PG_ADMIN_HOST, PGB_PORT, "pgbouncer", "pgbouncer",
        "SHOW CONFIG", timeout=10,
    )
    pool_mode_session_ok = False
    live_pool_mode: str | None = None
    if rc == 0:
        for line in out.splitlines():
            cols = line.split("|")
            if len(cols) >= 2 and cols[0].strip() == "pool_mode":
                live_pool_mode = cols[1].strip()
                break
        if live_pool_mode == "session":
            pool_mode_session_ok = True
    prosecutor["c_ordering_pgbouncer_live_pool_mode"] = live_pool_mode

    prepare_threshold_none_ok = False
    if APP_CONFIG.exists():
        text = APP_CONFIG.read_text(encoding="utf-8")
        if re.search(r"^PSYCOPG2_PREPARE_THRESHOLD\s*=\s*None\b",
                     text, re.MULTILINE):
            prepare_threshold_none_ok = True
    prosecutor["c_ordering_prepare_threshold_none"] = prepare_threshold_none_ok

    if not (pool_mode_session_ok or prepare_threshold_none_ok):
        prosecutor["c_ordering_disjunct_failure"] = (
            "both_pool_mode_session_and_psycopg2_prepare_threshold_None_missing"
        )
        return (False, "C_ORDERING")
    return (True, None)


def _c_divergence_catalog_content_hash(prosecutor: dict) -> tuple[bool, str | None]:
    try:
        baseline = json.loads(EXPECTED_CATALOG_HASH_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        prosecutor["c_divergence_holdout_read_error"] = repr(exc)[:400]
        return (False, "C_DIVERGENCE")
    expected = baseline.get("catalog_content_hash")
    if not expected:
        prosecutor["c_divergence_baseline_missing_hash"] = True
        return (False, "C_DIVERGENCE")

    env = os.environ.copy()
    env["PGPASSWORD"] = APP_PASSWORD
    try:
        proc = subprocess.run(
            ["psql", "-h", PG_ADMIN_HOST, "-p", str(PGB_PORT),
             "-U", APP_USER, "-d", APP_DB, "-tAc",
             "SELECT catalog_id, sku, description, price, "
             "array_to_string(tags, ',') FROM catalog ORDER BY catalog_id"],
            capture_output=True, timeout=60, env=env,
        )
    except subprocess.TimeoutExpired:
        prosecutor["c_divergence_catalog_query_timeout"] = True
        return (False, "C_DIVERGENCE")
    if proc.returncode != 0:
        prosecutor["c_divergence_catalog_query_rc"] = proc.returncode
        prosecutor["c_divergence_catalog_query_stderr_tail"] = \
            (proc.stderr or b"").decode("utf-8", errors="replace")[-400:]
        return (False, "C_DIVERGENCE")

    observed = hashlib.sha256(proc.stdout).hexdigest()
    prosecutor["c_divergence_catalog_content_hash_expected"] = expected
    prosecutor["c_divergence_catalog_content_hash_observed"] = observed
    if observed != expected:
        return (False, "C_DIVERGENCE")
    return (True, None)


def _rl5_setnx_call_count_delta(prosecutor: dict) -> tuple[bool, str | None]:
    before = prosecutor.get("setnx_call_count_before_replay")
    after = prosecutor.get("setnx_call_count_after_replay")
    if before is None or after is None or before < 0 or after < 0:
        prosecutor["rl5_setnx_delta_failure"] = "commandstats_snapshot_unavailable"
        return (False,
                "RL5_silent_removal_of_redis_setnx_cache_fill_mutex_primitive_detected")
    delta = after - before
    prosecutor["rl5_setnx_call_count_delta"] = delta
    if delta <= 0:
        return (False,
                "RL5_silent_removal_of_redis_setnx_cache_fill_mutex_primitive_detected")
    return (True, None)


def _rl5_worker_py_sha256_baseline(prosecutor: dict) -> tuple[bool, str | None]:
    if not WORKER_PY_PATH.exists():
        prosecutor["rl5_worker_py_baseline_failure"] = "worker_py_missing"
        return (False,
                "RL5_silent_removal_of_redis_setnx_cache_fill_mutex_primitive_detected")
    actual = hashlib.sha256(WORKER_PY_PATH.read_bytes()).hexdigest()
    prosecutor["rl5_worker_py_baseline_sha256_expected"] = WORKER_PY_BASELINE_SHA256
    prosecutor["rl5_worker_py_baseline_sha256_actual"] = actual
    if actual != WORKER_PY_BASELINE_SHA256:
        prosecutor["rl5_worker_py_baseline_failure"] = "sha256_mismatch"
        return (False,
                "RL5_silent_removal_of_redis_setnx_cache_fill_mutex_primitive_detected")
    return (True, None)


def _rl5_pg_stat_activity_semantic_poller(prosecutor: dict) -> tuple[bool, str | None]:
    max_seen = prosecutor.get("rl5_pg_stat_activity_max_concurrent_catalog_fill_scans")
    poll_error = prosecutor.get("rl5_pg_stat_activity_poll_error")
    if poll_error is not None:
        prosecutor.setdefault("rl5_pg_stat_activity_failure", poll_error)
        return (False,
                "RL5_silent_removal_of_redis_setnx_cache_fill_mutex_primitive_detected")
    if max_seen is None:
        prosecutor["rl5_pg_stat_activity_failure"] = "poller_never_recorded_a_sample"
        return (False,
                "RL5_silent_removal_of_redis_setnx_cache_fill_mutex_primitive_detected")
    prosecutor["rl5_pg_stat_activity_max_concurrent_catalog_fill_scans_threshold"] = \
        PG_STAT_ACTIVITY_MAX_CONCURRENT_CATALOG_FILL_SCANS
    if max_seen > PG_STAT_ACTIVITY_MAX_CONCURRENT_CATALOG_FILL_SCANS:
        prosecutor["rl5_pg_stat_activity_failure"] = "concurrent_catalog_fill_scans_exceed_threshold"
        return (False,
                "RL5_silent_removal_of_redis_setnx_cache_fill_mutex_primitive_detected")
    return (True, None)


def _pg_stat_activity_poller_thread(stop_event: "threading.Event",
                                    max_holder: list[int],
                                    error_holder: list[str]) -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = APP_PASSWORD
    while not stop_event.is_set():
        try:
            proc = subprocess.run(
                ["psql", "-h", PG_ADMIN_HOST, "-p", str(PGB_PORT),
                 "-U", APP_USER, "-d", APP_DB, "-tAc",
                 "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' "
                 "AND query LIKE '" + PG_STAT_ACTIVITY_CATALOG_FILL_QUERY_PATTERN + "'"],
                capture_output=True, text=True, timeout=3, env=env,
            )
        except subprocess.TimeoutExpired:
            error_holder.append("psql_poll_timeout")
            stop_event.wait(PG_STAT_ACTIVITY_POLL_INTERVAL_S)
            continue
        except Exception as exc:
            error_holder.append(f"psql_poll_exception:{type(exc).__name__}")
            stop_event.wait(PG_STAT_ACTIVITY_POLL_INTERVAL_S)
            continue
        if proc.returncode == 0:
            try:
                count = int((proc.stdout or "0").strip())
            except ValueError:
                count = -1
            if count >= 0 and count > (max_holder[0] if max_holder else 0):
                if max_holder:
                    max_holder[0] = count
                else:
                    max_holder.append(count)
            elif not max_holder:
                max_holder.append(0)
        stop_event.wait(PG_STAT_ACTIVITY_POLL_INTERVAL_S)


def d4_five_check_family() -> tuple[bool, str | None, dict]:
    prosecutor: dict = {}

    baseline_ok, baseline_reason = _rl5_worker_py_sha256_baseline(prosecutor)
    if not baseline_ok:
        return (False, baseline_reason or "RL5", prosecutor)

    ok, sub_prosecutor = _c_value_run_worker_replay()
    prosecutor.update(sub_prosecutor)
    if not ok:
        return (False, "D4_C_VALUE_or_C_INVARIANT_or_C_ABSENCE_or_C_ORDERING_or_C_DIVERGENCE_check_failed_across_post_remediation_worker_replay_window",
                prosecutor)

    rl5_ok, rl5_reason = _rl5_setnx_call_count_delta(prosecutor)
    if not rl5_ok:
        return (False, rl5_reason or "RL5", prosecutor)

    behavior_ok, behavior_reason = _rl5_pg_stat_activity_semantic_poller(prosecutor)
    if not behavior_ok:
        return (False, behavior_reason or "RL5", prosecutor)

    for check_fn in (
        _c_invariant_row_counts,
        _c_absence_log_scans,
        _c_ordering_pool_mode_or_prepare_threshold,
        _c_divergence_catalog_content_hash,
    ):
        ok, failing_check = check_fn(prosecutor)
        if not ok:
            prosecutor["first_failing_check"] = failing_check
            return (False,
                    "D4_C_VALUE_or_C_INVARIANT_or_C_ABSENCE_or_C_ORDERING_or_C_DIVERGENCE_check_failed_across_post_remediation_worker_replay_window",
                    prosecutor)

    return (True, None, prosecutor)


def main() -> int:
    ok, reason, prosecutor = d1_files_present()
    if not ok:
        emit_reward(0.0, reason, prosecutor)
        return 1

    ok, reason, prosecutor = d5_shortcut_scan()
    if not ok:
        emit_reward(0.0, reason, prosecutor)
        return 1

    ok, reason, prosecutor = d6_line_budget()
    if not ok:
        emit_reward(0.0, reason, prosecutor)
        return 1
    d6_prosecutor = prosecutor

    ok, reason, prosecutor = d2_run_patch_and_check_readiness()
    if not ok:
        emit_reward(0.0, reason, prosecutor)
        return 1
    d2_prosecutor = prosecutor

    time.sleep(POST_STABILIZATION_S)

    ok, reason, prosecutor = d3_runbook_parse()
    if not ok:
        emit_reward(0.0, reason, prosecutor)
        return 1

    ok, reason, prosecutor = d4_five_check_family()
    if not ok:
        emit_reward(0.0, reason, prosecutor)
        return 1
    d4_prosecutor = prosecutor

    emit_reward(1.0, "all_deliverables_passed",
                {"d2": d2_prosecutor,
                 "d4": d4_prosecutor,
                 "combined_line_budget_report": d6_prosecutor})
    return 0


if __name__ == "__main__":
    sys.exit(main())
