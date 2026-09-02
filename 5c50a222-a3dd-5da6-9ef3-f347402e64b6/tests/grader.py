#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REWARD_PATH = os.environ.get("REWARD_PATH", "/logs/verifier/reward.json")
WORKSPACE = Path("/workspace")
PATCH_SH = WORKSPACE / "patch.sh"
RUNBOOK_MD = WORKSPACE / "runbook.md"
AUDIT_LOG = Path("/var/log/app/audit.log")
PROM_BASE = "http://127.0.0.1:9090"
APP_BASE = "http://127.0.0.1:8080"

CANONICAL_ROUTES = ("/api/list", "/api/get", "/api/put", "/health")
CANONICAL_STATUSES = ("200", "400", "500")
CANONICAL_SERIES = frozenset(
    (r, s) for r in CANONICAL_ROUTES for s in CANONICAL_STATUSES
)

DIVERGENCE_TOLERANCE = 40
COMBINED_LINE_BUDGET = 200
READINESS_TIMEOUT_S = 15
POST_STABILIZATION_S = 20
SCRAPE_INTERVAL_S = 5
POST_PATCH_SCRAPES = 3

SHORTCUT_PATTERNS = (
    (r"\brule_files\s*:", "RL1_recording_rule_synthesizing_graded_namespace"),
    (r"^\s*record\s*:\s*http_requests_total",
     "RL1_recording_rule_synthesizing_graded_namespace"),
    (r"\brelabel_configs\s*:", "RL2_relabel_configs_synthesizing_graded_labels"),
    (r"\bmetric_relabel_configs\s*:",
     "RL2_relabel_configs_synthesizing_graded_labels"),
    (r"\bremote_write\s*:", "RL3_federation_or_remote_write_or_remote_read"),
    (r"\bremote_read\s*:", "RL3_federation_or_remote_write_or_remote_read"),
    (r"honor_labels\s*:\s*true", "RL3_federation_or_remote_write_or_remote_read"),
    (r"/federate\b", "RL3_federation_or_remote_write_or_remote_read"),
    (r"/api/v1/admin/tsdb/(?:delete_series|snapshot|clean_tombstones)",
     "RL4_admin_api_tsdb_write_on_graded_series"),
    (r"--web\.enable-admin-api", "RL4_admin_api_tsdb_write_on_graded_series"),
    (r">>?\s*/var/log/app/audit\.log\b",
     "RL5_audit_log_rewrite_or_truncate_or_delete"),
    (r"\btruncate\b[^\n]*/var/log/app/audit\.log",
     "RL5_audit_log_rewrite_or_truncate_or_delete"),
    (r"\bsed\b[^\n]*-i[^\n]*/var/log/app/audit\.log",
     "RL5_audit_log_rewrite_or_truncate_or_delete"),
    (r"\b(?:rm|mv|cp)\b[^\n]*/var/log/app/audit\.log",
     "RL5_audit_log_rewrite_or_truncate_or_delete"),
    (r"open\(\s*['\"]/var/log/app/audit\.log['\"]\s*,\s*['\"](?:w|a\+|r\+)",
     "RL5_audit_log_rewrite_or_truncate_or_delete"),
    (r"/opt/holdout\b", "shortcut_private_holdout_path"),
    (r"\bapt(?:-get)?\s+install\b",
     "shortcut_runtime_install_or_network_family"),
    (r"\bpip3?\s+install\b", "shortcut_runtime_install_or_network_family"),
    (r"\bnpm\s+install\b", "shortcut_runtime_install_or_network_family"),
    (r"\bcargo\s+install\b", "shortcut_runtime_install_or_network_family"),
    (r"\bcurl\b[^\n]*https?://(?!(?:127\.0\.0\.1|localhost|\[::1\]|0\.0\.0\.0)(?::|/|\b))",
     "shortcut_runtime_install_or_network_family"),
    (r"\bwget\b[^\n]*https?://(?!(?:127\.0\.0\.1|localhost|\[::1\]|0\.0\.0\.0)(?::|/|\b))",
     "shortcut_runtime_install_or_network_family"),
    (r"\bgit\s+clone\b", "shortcut_runtime_install_or_network_family"),
)

FORBIDDEN_PRE_MUTATION_LITERALS = (
    'route="/api/list",status="200"',
    'route="/api/list",status="400"',
    'route="/api/list",status="500"',
    'route="/api/get",status="200"',
    'route="/api/put",status="200"',
    'route="/health",status="200"',
    "monitor=\"forge-inv25\"",
    "instance=\"app-local\",job=\"app\"",
)

RUNBOOK_SECTION_HEADERS = ("### SYMPTOM", "### ROOT-CAUSE", "### FIX")
RUNBOOK_KEYS = ("detected_by:", "evidence:", "reconciliation:")


def emit_reward(reward, reason, prosecutor=None):
    flat: dict = {"reward": float(reward)}
    for k, v in (prosecutor or {}).items():
        flat[f"p_{k}"] = int(v) if isinstance(v, bool) else v
    Path(REWARD_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(REWARD_PATH).write_text(json.dumps(flat, sort_keys=True) + "\n", encoding="utf-8")


def d1_files_present():
    if not PATCH_SH.exists() or not RUNBOOK_MD.exists():
        return (False, "D1_authored_files_missing_or_empty_or_invalid_utf8_or_patch_sh_not_executable",
                {"authored_files_present": {
                    "patch_sh": PATCH_SH.exists(),
                    "runbook_md": RUNBOOK_MD.exists(),
                }})
    if PATCH_SH.stat().st_size == 0 or RUNBOOK_MD.stat().st_size == 0:
        return (False, "D1_authored_files_missing_or_empty_or_invalid_utf8_or_patch_sh_not_executable",
                {"authored_files_present": {
                    "patch_sh_bytes": PATCH_SH.stat().st_size,
                    "runbook_md_bytes": RUNBOOK_MD.stat().st_size,
                }})
    try:
        PATCH_SH.read_bytes().decode("utf-8")
        RUNBOOK_MD.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return (False, "D1_authored_files_missing_or_empty_or_invalid_utf8_or_patch_sh_not_executable",
                {"authored_files_present": {"utf8": False}})
    if not os.access(PATCH_SH, os.X_OK):
        return (False, "D1_authored_files_missing_or_empty_or_invalid_utf8_or_patch_sh_not_executable",
                {"authored_files_present": {"patch_sh_executable": False}})
    return (True, None, None)


def d5_shortcut_scan():
    files = {"patch.sh": PATCH_SH, "runbook.md": RUNBOOK_MD}
    for label, path in files.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        for pat, rl_id in SHORTCUT_PATTERNS:
            m = re.search(pat, text, re.MULTILINE)
            if m:
                first_word = rl_id.split("_")[0]
                if first_word.startswith("RL"):
                    reason = first_word.replace("RL1", "RL1_recording_rule_synthesizing_graded_namespace_detected") \
                                     .replace("RL2", "RL2_relabel_or_metric_relabel_synthesizing_graded_labels_detected") \
                                     .replace("RL3", "RL3_federation_or_remote_write_or_remote_read_detected") \
                                     .replace("RL4", "RL4_admin_api_tsdb_call_detected") \
                                     .replace("RL5", "RL5_audit_log_rewrite_or_truncate_or_delete_detected")
                else:
                    reason = "D5_authored_file_matches_bound_shortcut_pattern"
                return (False, reason, {
                    "matched_shortcut_pattern": rl_id,
                    "matched_shortcut_pattern_file_path": str(path),
                    "matched_shortcut_pattern_byte_offset": m.start(),
                    "red_line_triggered": first_word if first_word.startswith("RL") else "",
                })
    return (True, None, None)


def d6_line_budget():
    total = len(PATCH_SH.read_bytes().splitlines()) + \
            len(RUNBOOK_MD.read_bytes().splitlines())
    if total > COMBINED_LINE_BUDGET:
        return (False, "D6_combined_line_count_exceeds_budget",
                {"combined_line_count": total,
                 "combined_line_budget": COMBINED_LINE_BUDGET})
    return (True, None, {"combined_line_count": total,
                         "combined_line_budget": COMBINED_LINE_BUDGET})


def _http_get(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read()
    except Exception as exc:
        return None, str(exc).encode("utf-8", errors="replace")


def _supervisorctl_status(name):
    try:
        out = subprocess.check_output(
            ["supervisorctl", "-c", "/etc/supervisor/supervisord.conf",
             "status", name],
            text=True, timeout=5,
        )
    except subprocess.CalledProcessError as exc:
        return exc.output.strip() if exc.output else ""
    except Exception:
        return ""
    return out.strip()


def _poll_until(fn, timeout_s, interval_s=1):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if fn():
            return True
        time.sleep(interval_s)
    return fn()


def d2_run_patch_and_check_readiness():
    audit_stat_pre = AUDIT_LOG.stat() if AUDIT_LOG.exists() else None
    first_line_pre = b""
    if AUDIT_LOG.exists() and AUDIT_LOG.stat().st_size > 0:
        with open(AUDIT_LOG, "rb") as fh:
            first_line_pre = fh.readline()[:256]
    t_readiness_start = time.monotonic()
    proc = subprocess.run(
        ["bash", str(PATCH_SH)],
        cwd=str(WORKSPACE),
        env={**os.environ, "LC_ALL": "C"},
        timeout=180,
    )
    if proc.returncode != 0:
        return (False, "D2_patch_sh_exit_nonzero_or_supervisorctl_status_app_not_running_or_metrics_not_http_200_within_readiness_window",
                {"patch_sh_exit_code": proc.returncode})
    app_ok = _poll_until(
        lambda: "RUNNING" in _supervisorctl_status("app"),
        READINESS_TIMEOUT_S,
    )
    prom_ok = _poll_until(
        lambda: "RUNNING" in _supervisorctl_status("prometheus"),
        READINESS_TIMEOUT_S,
    )
    metrics_ok = _poll_until(
        lambda: _http_get(APP_BASE + "/metrics")[0] == 200,
        READINESS_TIMEOUT_S,
    )
    ready_ok = _poll_until(
        lambda: _http_get(PROM_BASE + "/-/ready")[0] == 200,
        READINESS_TIMEOUT_S,
    )
    elapsed_ms = int((time.monotonic() - t_readiness_start) * 1000)
    prosecutor = {
        "patch_sh_exit_code": 0,
        "supervisorctl_app_status": _supervisorctl_status("app"),
        "metrics_http_status": _http_get(APP_BASE + "/metrics")[0] or 0,
        "readiness_ms_elapsed": elapsed_ms,
    }
    if audit_stat_pre is not None:
        prosecutor["audit_log_inode_at_agent_start"] = audit_stat_pre.st_ino
        prosecutor["audit_log_size_at_agent_start"] = audit_stat_pre.st_size
        prosecutor["audit_log_first_line_bytes_at_agent_start"] = \
            first_line_pre.decode("utf-8", errors="replace")
    if AUDIT_LOG.exists():
        st = AUDIT_LOG.stat()
        prosecutor["audit_log_inode_at_verifier_start"] = st.st_ino
        prosecutor["audit_log_size_at_verifier_start"] = st.st_size
        with open(AUDIT_LOG, "rb") as fh:
            prosecutor["audit_log_first_line_bytes_at_verifier_start"] = \
                fh.readline()[:256].decode("utf-8", errors="replace")
    if not (app_ok and prom_ok and metrics_ok and ready_ok):
        return (False, "D2_patch_sh_exit_nonzero_or_supervisorctl_status_app_not_running_or_metrics_not_http_200_within_readiness_window",
                prosecutor)
    if AUDIT_LOG.exists() and audit_stat_pre is not None:
        st = AUDIT_LOG.stat()
        if st.st_ino != audit_stat_pre.st_ino:
            return (False, "RL5_audit_log_rewrite_or_truncate_or_delete_detected",
                    prosecutor)
        if st.st_size < audit_stat_pre.st_size:
            return (False, "RL5_audit_log_rewrite_or_truncate_or_delete_detected",
                    prosecutor)
        if audit_stat_pre.st_size > 0 and first_line_pre:
            with open(AUDIT_LOG, "rb") as fh:
                first_line_now = fh.readline()[:256]
            if first_line_now != first_line_pre:
                return (False, "RL5_audit_log_rewrite_or_truncate_or_delete_detected",
                        prosecutor)
    return (True, None, prosecutor)


def d3_runbook_parse():
    text = RUNBOOK_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    header_positions = []
    for i, ln in enumerate(lines):
        if ln.strip() in RUNBOOK_SECTION_HEADERS:
            header_positions.append((i, ln.strip()))
    if len(header_positions) != 3:
        return (False, "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_mutation_evidence_literal_in_runbook",
                {"runbook_parse_failing_section": "count_mismatch",
                 "runbook_parse_failing_line_number": -1})
    order = [h[1] for h in header_positions]
    if order != list(RUNBOOK_SECTION_HEADERS):
        return (False, "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_mutation_evidence_literal_in_runbook",
                {"runbook_parse_failing_section": "order_mismatch",
                 "runbook_parse_failing_line_number": header_positions[0][0] + 1})
    for si, (idx, header) in enumerate(header_positions):
        end = header_positions[si + 1][0] if si + 1 < len(header_positions) else len(lines)
        body_lines = [ln for ln in lines[idx + 1:end] if ln.strip()]
        kv_lines = [ln for ln in body_lines
                    if any(ln.strip().startswith(k) for k in RUNBOOK_KEYS)]
        if len(kv_lines) != 3:
            return (False, "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_mutation_evidence_literal_in_runbook",
                    {"runbook_parse_failing_section": header,
                     "runbook_parse_failing_key": "kv_count",
                     "runbook_parse_failing_line_number": idx + 1})
        for ki, key in enumerate(RUNBOOK_KEYS):
            if not kv_lines[ki].strip().startswith(key):
                return (False, "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_mutation_evidence_literal_in_runbook",
                        {"runbook_parse_failing_section": header,
                         "runbook_parse_failing_key": key,
                         "runbook_parse_failing_line_number": idx + 1,
                         "runbook_parse_offending_line_text": kv_lines[ki][:200]})
    for lit in FORBIDDEN_PRE_MUTATION_LITERALS:
        if lit in text:
            return (False, "D3_runbook_md_does_not_parse_under_fixed_three_section_schema_or_key_value_regex_mismatch_or_pre_mutation_evidence_literal_in_runbook",
                    {"pre_mutation_evidence_literal_hit": lit})
    return (True, None, None)


def _promql_instant(query):
    url = PROM_BASE + "/api/v1/query?query=" + urllib.parse.quote(query)
    status, body = _http_get(url, timeout=10)
    if status != 200:
        return None
    try:
        data = json.loads(body)
    except Exception:
        return None
    if data.get("status") != "success":
        return None
    return data.get("data", {}).get("result", [])


def _series_by_pair(result):
    out = {}
    for series in result:
        m = series.get("metric", {})
        route = m.get("route", "")
        status = m.get("status", "")
        try:
            val = float(series["value"][1])
        except (KeyError, IndexError, ValueError):
            continue
        out[(route, status)] = val
    return out


def _rules_api_scan():
    status, body = _http_get(PROM_BASE + "/api/v1/rules")
    if status != 200:
        return "unreachable"
    try:
        data = json.loads(body)
    except Exception:
        return "unparseable"
    groups = data.get("data", {}).get("groups", [])
    return "empty" if not groups else "non_empty"


def _prometheus_yml_parse():
    try:
        import yaml
    except Exception:
        return "no_yaml_module"
    try:
        with open("/etc/prometheus/prometheus.yml", "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
    except Exception as exc:
        return "parse_error: " + str(exc)[:120]
    banned = []
    if cfg.get("rule_files"):
        banned.append("rule_files")
    for job in cfg.get("scrape_configs", []) or []:
        if job.get("relabel_configs"):
            banned.append("relabel_configs")
        if job.get("metric_relabel_configs"):
            banned.append("metric_relabel_configs")
        if job.get("honor_labels") is True:
            banned.append("honor_labels_true")
        if job.get("metrics_path") == "/federate":
            banned.append("federate_metrics_path")
    if cfg.get("remote_write"):
        banned.append("remote_write")
    if cfg.get("remote_read"):
        banned.append("remote_read")
    return "clean" if not banned else "banned:" + ",".join(banned)


def _count_audit_in_window(t0_ms, t1_ms):
    counts = {}
    if not AUDIT_LOG.exists():
        return counts
    with open(AUDIT_LOG, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            try:
                ts = int(rec["ts"])
            except (KeyError, ValueError, TypeError):
                continue
            if t0_ms - 5000 <= ts <= t1_ms + 5000:
                key = (str(rec.get("route", "")), str(rec.get("status", "")))
                counts[key] = counts.get(key, 0) + 1
    return counts


def d4_five_check_family():
    rules_scan = _rules_api_scan()
    yml_scan = _prometheus_yml_parse()
    if rules_scan == "non_empty":
        return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                {"first_failing_check": "C_ABSENCE",
                 "rules_api_scan_result": rules_scan,
                 "prometheus_yml_yaml_parse_result": yml_scan})
    if yml_scan.startswith("banned:"):
        return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                {"first_failing_check": "C_ABSENCE",
                 "rules_api_scan_result": rules_scan,
                 "prometheus_yml_yaml_parse_result": yml_scan})
    prior_values = {}
    scrape_records = []
    for scrape_i in range(POST_PATCH_SCRAPES):
        t0 = int(time.time() * 1000)
        time.sleep(SCRAPE_INTERVAL_S + 1)
        t1 = int(time.time() * 1000)
        result = _promql_instant("http_requests_total")
        if result is None:
            return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                    {"first_failing_check": "C_ORDERING",
                     "scrape_ordering_gap_seconds_observed": (t1 - t0) // 1000,
                     "promql_query_response_shape_observed": "unreachable_or_error",
                     "promql_query_response_shape_expected": "success_with_twelve_series"})
        by_pair = _series_by_pair(result)
        observed_keys = set(by_pair.keys())
        if observed_keys != CANONICAL_SERIES:
            extra = sorted(observed_keys - CANONICAL_SERIES)[:5]
            missing = sorted(CANONICAL_SERIES - observed_keys)[:5]
            return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                    {"first_failing_check": "C_VALUE" if len(observed_keys) != 12 else "C_ABSENCE",
                     "first_failing_check_expected_value": "12_canonical_series",
                     "first_failing_check_observed_value": "count=" + str(len(observed_keys)) + " extra=" + repr(extra) + " missing=" + repr(missing),
                     "promql_query_response_shape_observed": "count=" + str(len(observed_keys)),
                     "promql_query_response_shape_expected": "count=12"})
        for pair, val in by_pair.items():
            if val < 0:
                return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                        {"first_failing_check": "C_INVARIANT",
                         "divergence_route": pair[0], "divergence_status": pair[1],
                         "divergence_promql_value": int(val)})
            if pair in prior_values and val < prior_values[pair]:
                return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                        {"first_failing_check": "C_INVARIANT",
                         "divergence_route": pair[0], "divergence_status": pair[1],
                         "divergence_promql_value": int(val)})
        audit = _count_audit_in_window(t0, t1)
        window_sum = sum(audit.values())
        if window_sum == 0:
            return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                    {"first_failing_check": "C_ORDERING",
                     "scrape_ordering_gap_seconds_observed": (t1 - t0) // 1000})
        prior_values = dict(by_pair)
        scrape_records.append({"scrape": scrape_i, "series_count": len(by_pair),
                               "audit_events_in_window": window_sum})
    baseline_pairs = {(r, s): _series_by_pair(_promql_instant("http_requests_total")).get((r, s), 0)
                      for r in CANONICAL_ROUTES for s in CANONICAL_STATUSES}
    t0_final = int(time.time() * 1000)
    time.sleep(SCRAPE_INTERVAL_S + 1)
    t1_final = int(time.time() * 1000)
    final_result = _promql_instant("http_requests_total")
    if final_result is None:
        return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                {"first_failing_check": "C_DIVERGENCE"})
    final_by_pair = _series_by_pair(final_result)
    audit_window = _count_audit_in_window(t0_final, t1_final)
    for r in CANONICAL_ROUTES:
        for s in CANONICAL_STATUSES:
            pair = (r, s)
            audit_count = audit_window.get(pair, 0)
            prom_delta = int(final_by_pair.get(pair, 0) - baseline_pairs.get(pair, 0))
            delta = abs(audit_count - prom_delta)
            if delta > DIVERGENCE_TOLERANCE:
                return (False, "D4_C_VALUE_series_count_not_twelve_or_C_INVARIANT_counter_reset_inside_post_stabilization_window_or_negative_rate_or_C_ABSENCE_recording_rule_or_relabel_synthesis_or_federation_detected_or_C_ORDERING_scrape_gap_or_zero_scrape_or_C_DIVERGENCE_promql_diverges_from_audit_log_beyond_jitter_tolerance",
                        {"first_failing_check": "C_DIVERGENCE",
                         "divergence_route": r, "divergence_status": s,
                         "divergence_promql_value": prom_delta,
                         "divergence_audit_log_count": audit_count,
                         "divergence_delta": delta,
                         "divergence_jitter_tolerance": DIVERGENCE_TOLERANCE})
    return (True, None, {"scrape_records": scrape_records,
                         "rules_api_scan_result": rules_scan,
                         "prometheus_yml_yaml_parse_result": yml_scan})


def main():
    ok, reason, prosecutor = d1_files_present()
    if not ok:
        emit_reward(0.0, reason, prosecutor); return 1
    ok, reason, prosecutor = d5_shortcut_scan()
    if not ok:
        emit_reward(0.0, reason, prosecutor); return 1
    ok, reason, prosecutor = d6_line_budget()
    if not ok:
        emit_reward(0.0, reason, prosecutor); return 1
    ok, reason, prosecutor = d2_run_patch_and_check_readiness()
    if not ok:
        emit_reward(0.0, reason, prosecutor); return 1
    d2_prosecutor = prosecutor
    time.sleep(POST_STABILIZATION_S)
    ok, reason, prosecutor = d3_runbook_parse()
    if not ok:
        emit_reward(0.0, reason, prosecutor); return 1
    ok, reason, prosecutor = d4_five_check_family()
    if not ok:
        emit_reward(0.0, reason, prosecutor); return 1
    emit_reward(1.0, "all_deliverables_passed",
                {"d2": d2_prosecutor, "d4": prosecutor,
                 "combined_line_budget": COMBINED_LINE_BUDGET})
    return 0


if __name__ == "__main__":
    sys.exit(main())
