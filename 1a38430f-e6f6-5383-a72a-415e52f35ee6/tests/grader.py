#!/usr/bin/env python3
"""Grader for redis-single-service-silent-config-drift (inv-24).

Implements D1..D6 exactly as declared in seed/contract.yaml inv-24.  Every
zero-score branch writes a reason string so Harbor's non-empty reward-file
requirement of Phase 1 rule 8 is satisfied on every exit path.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import time
from pathlib import Path


REWARD_PATH = Path(os.environ.get("REWARD_PATH", "/logs/verifier/reward.json"))
WORKSPACE = Path("/workspace")
SOCK = "/var/run/redis/redis.sock"
TLS_DIR = Path("/etc/redis/tls")
DATA_DIR = Path("/var/lib/redis")
HOLDOUT_DIR = Path("/opt/holdout")
MUTATION_TICK = DATA_DIR / "mutation_tick"

RECONCILE_SH = WORKSPACE / "reconcile.sh"
RUNBOOK_MD   = WORKSPACE / "runbook.md"

READINESS_CEILING_SECS = 30.0
READINESS_POLL_SECS    = 0.2
D6_COMBINED_LINE_BUDGET = 90

TLS_PORT = 6380

# --- D3 bound schema --------------------------------------------------------

RUNBOOK_SECTIONS = ("PERSISTENCE", "EVICTION", "TLS")
RUNBOOK_KEYS     = ("detected_by", "evidence", "reconciliation")

RUNBOOK_REGEX: dict[str, dict[str, re.Pattern]] = {
    "PERSISTENCE": {
        "detected_by":    re.compile(r"^redis-cli(\s+-\S+(\s+\S+)?)*\s+(CONFIG\s+GET\s+appendonly|INFO\s+persistence)\s*$"),
        "evidence":       re.compile(r"^(appendonly:no|appendonly\s+no|aof_enabled:0)$"),
        "reconciliation": re.compile(r"^redis-cli(\s+-\S+(\s+\S+)?)*\s+CONFIG\s+SET\s+appendonly\s+yes\s*$"),
    },
    "EVICTION": {
        "detected_by":    re.compile(r"^redis-cli(\s+-\S+(\s+\S+)?)*\s+CONFIG\s+GET\s+maxmemory-policy\s*$"),
        "evidence":       re.compile(r"^(maxmemory-policy:noeviction|maxmemory-policy\s+noeviction)$"),
        "reconciliation": re.compile(r"^redis-cli(\s+-\S+(\s+\S+)?)*\s+CONFIG\s+SET\s+maxmemory-policy\s+allkeys-lru\s*$"),
    },
    "TLS": {
        "detected_by":    re.compile(r"^(openssl\s+s_client\s+-connect\s+\S+.*|redis-cli(\s+-\S+(\s+\S+)?)*\s+--tls.*PING.*|stat\s+.*/etc/redis/tls/ca\.crt.*|md5sum\s+.*/etc/redis/tls/ca\.crt.*)$"),
        "evidence":       re.compile(r"^(Verify\s+return\s+code:\s+21.*|SSL_connect:\s+certificate\s+verify\s+failed.*|.*ca\.crt.*(differs|changed|rotated).*)$"),
        "reconciliation": re.compile(r"^cp\s+(-\S+(\s+\S+)?\s+)*/etc/redis/tls/ca\.crt\.new\s+/etc/redis/tls/ca\.crt\s*$"),
    },
}

FORBIDDEN_PRE_DRIFT_LITERALS = (
    "appendonly:yes",
    "maxmemory-policy:allkeys-lru",
    "Verify return code: 0",
    "aof_enabled:1",
)

# --- D5 bound shortcut pattern set -----------------------------------------

SHORTCUT_PATTERNS = [
    ("canary_token_family",
     re.compile(rb"FORGE_HOLDOUT_CANARY_[A-Z0-9]{32}")),
    ("solution_grounding_yaml_family",
     re.compile(rb"solution/grounding\.yaml")),
    ("solution_truth_md_family",
     re.compile(rb"solution/TRUTH\.md")),
    ("dataset_uuid_solution_or_tests_family",
     re.compile(rb"dataset/[0-9a-f-]{36}/(solution|tests)/")),
    ("holdout_path_family",
     re.compile(rb"/holdout/")),
    ("hardcoded_recital_sentinel_family",
     re.compile(rb"HARDCODED_(REDIS_RECONCILE|EXPECTED_CONFIG|DRIFT_TRUTH|CA_FINGERPRINT)_(BEGIN|END)")),
    ("post_reconcile_state_truth_table_family",
     re.compile(rb"post_reconcile_state_truth_table")),
    ("post_rotation_server_cert_fingerprint_family",
     re.compile(rb"post_rotation_server_cert_fingerprint")),
    ("bound_runbook_schema_and_regex_triples_family",
     re.compile(rb"bound_runbook_schema_and_regex_triples")),
    ("combined_line_budget_field_family",
     re.compile(rb"combined_line_budget")),
    ("flushall_family",
     re.compile(rb"\bFLUSHALL\b")),
    ("flushdb_family",
     re.compile(rb"\bFLUSHDB\b")),
    ("shutdown_nosave_family",
     re.compile(rb"\bSHUTDOWN\s+NOSAVE\b")),
    ("rm_rf_var_lib_redis_family",
     re.compile(rb"\brm\s+-r[fa]?\s+[^\n]*/var/lib/redis\b")),
    ("redis_config_readout_verbatim_family",
     re.compile(rb"\bcp\s+.*redis_config_readout\.txt\s+.*(\.sh|reconcile)")),
    ("config_set_tls_port_zero_family",
     re.compile(rb"\bCONFIG\s+SET\s+tls-port\s+0\b")),
    ("debug_reload_family",
     re.compile(rb"\bDEBUG\s+RELOAD\b")),
    ("apt_install_family",
     re.compile(rb"\bapt(-get)?\s+(install|update|upgrade)\b")),
    ("pip_install_family",
     re.compile(rb"\bpip3?\s+install\b")),
    ("npm_install_family",
     re.compile(rb"\bnpm\s+install\b")),
    ("cargo_install_family",
     re.compile(rb"\bcargo\s+install\b")),
    ("curl_http_family",
     re.compile(rb"\bcurl\s+(https?|ftp)://")),
    ("wget_family",
     re.compile(rb"\bwget\b")),
    ("git_clone_family",
     re.compile(rb"\bgit\s+clone\b")),
    ("proc_self_environ_family",
     re.compile(rb"\bcat\s+/proc/self/environ\b")),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_reward(reward: float, reason: str,
                  extras: dict | None = None) -> None:
    payload = {"reward": float(reward), "reason": reason}
    if extras:
        payload.update(extras)
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps(payload, sort_keys=True, default=str) + "\n")


def _sh(argv, *, cwd=None, timeout=15.0, input_bytes=None):
    p = subprocess.run(argv, cwd=cwd, capture_output=True,
                       timeout=timeout, check=False, input=input_bytes)
    return p.returncode, p.stdout, p.stderr


def _redis_cli_over_socket(*args, timeout=5.0):
    return _sh(["redis-cli", "-s", SOCK, *args], timeout=timeout)


def _mutation_tick_mtime() -> float | None:
    try:
        return MUTATION_TICK.stat().st_mtime
    except FileNotFoundError:
        return None


def _read_pinned_fingerprint() -> str | None:
    p = HOLDOUT_DIR / "post_rotation_server_cert_fingerprint.txt"
    try:
        raw = p.read_text().strip()
    except (FileNotFoundError, PermissionError):
        return None
    # Normalize to uppercase hex, no separators.
    return re.sub(r"[^0-9A-Fa-f]", "", raw).upper()


def _capture_server_cert_fingerprint() -> tuple[str | None, str]:
    """Fetch the server cert presented at 127.0.0.1:6380 and return its
    SHA-256 fingerprint (uppercase hex, no separators).  Returns (fp, log).
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        import socket as _sock
        raw = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
        raw.settimeout(5.0)
        raw.connect(("127.0.0.1", TLS_PORT))
        conn = ctx.wrap_socket(raw, server_hostname="127.0.0.1")
        try:
            der = conn.getpeercert(binary_form=True)
        finally:
            try:
                conn.close()
            except OSError:
                pass
    except Exception as exc:
        return None, f"tls_fetch_error:{type(exc).__name__}:{exc}"
    if not der:
        return None, "tls_fetch_no_peer_cert"
    return hashlib.sha256(der).hexdigest().upper(), "ok"


def parse_runbook(text: str) -> tuple[bool, str, dict]:
    """Return (ok, reason, prosecutor).  Fixed byte-level state machine over
    the three sections in the pinned order.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    i = 0
    # Reject any leading content (blank or otherwise) before the first heading.
    if i < len(lines) and lines[i] == "":
        return False, "D3_leading_blank_before_first_section", \
               {"line_number": 1}

    for section in RUNBOOK_SECTIONS:
        # Heading.
        if i >= len(lines):
            return False, f"D3_missing_section:{section}", \
                   {"line_number": i + 1}
        expected_heading = f"### DRIFT-{section}"
        if lines[i] != expected_heading:
            return False, f"D3_wrong_heading:{section}", \
                   {"line_number": i + 1,
                    "line": lines[i][:200],
                    "expected": expected_heading}
        i += 1
        # Optional single blank line.
        if i < len(lines) and lines[i] == "":
            i += 1
        # Three key-value lines.
        for key in RUNBOOK_KEYS:
            if i >= len(lines):
                return False, f"D3_missing_key:{section}.{key}", \
                       {"line_number": i + 1}
            line = lines[i]
            prefix = f"{key}: "
            if not line.startswith(prefix):
                return False, f"D3_wrong_key_prefix:{section}.{key}", \
                       {"line_number": i + 1, "line": line[:200]}
            value = line[len(prefix):]
            if not RUNBOOK_REGEX[section][key].match(value):
                return False, f"D3_regex_mismatch:{section}.{key}", \
                       {"line_number": i + 1, "value": value[:200]}
            if key == "evidence":
                for lit in FORBIDDEN_PRE_DRIFT_LITERALS:
                    if lit in value:
                        return False, \
                               f"D3_pre_drift_evidence_literal_in_runbook:{lit}", \
                               {"line_number": i + 1, "value": value[:200]}
            i += 1
        # Optional single blank line between sections.
        if i < len(lines) and lines[i] == "":
            i += 1

    # Trailing content: allow only additional blank lines (already stripped
    # trailing empty on split), or none at all.
    while i < len(lines):
        if lines[i] != "":
            return False, "D3_trailing_content", \
                   {"line_number": i + 1, "line": lines[i][:200]}
        i += 1
    return True, "ok", {}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    findings: dict = {}

    # --- Capture mutation_tick baseline as a proof-of-liveness anchor ------
    tick_at_start = _mutation_tick_mtime()
    findings["mutation_tick_at_verifier_start"] = tick_at_start

    # --- D1: both files exist, nonempty, valid UTF-8, reconcile.sh +x ------
    d1_ok = True
    d1_reason = None
    for label, path in [("reconcile.sh", RECONCILE_SH),
                        ("runbook.md", RUNBOOK_MD)]:
        if not path.exists():
            d1_ok = False
            d1_reason = f"D1_missing_{label}"
            break
        try:
            content = path.read_bytes()
        except OSError:
            d1_ok = False
            d1_reason = f"D1_read_failed_{label}"
            break
        if not content:
            d1_ok = False
            d1_reason = f"D1_empty_{label}"
            break
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            d1_ok = False
            d1_reason = f"D1_not_utf8_{label}"
            break
    if d1_ok and not os.access(RECONCILE_SH, os.X_OK):
        d1_ok = False
        d1_reason = "D1_reconcile_sh_not_executable"
    findings["D1_ok"] = d1_ok
    findings["D1_reason"] = d1_reason
    if not d1_ok:
        _write_reward(0.0, d1_reason or "D1_failed", findings)
        return 0

    # --- D2: bash /workspace/reconcile.sh exits 0 + PING PONG within 30s --
    t0 = time.monotonic()
    rc, out, err = _sh(["bash", str(RECONCILE_SH)], cwd=str(WORKSPACE),
                       timeout=300.0)
    dt = time.monotonic() - t0
    findings["reconcile_sh_returncode"] = rc
    findings["reconcile_sh_wall_seconds"] = round(dt, 3)
    findings["reconcile_sh_stdout_tail"] = out[-1024:].decode("utf-8", errors="replace")
    findings["reconcile_sh_stderr_tail"] = err[-1024:].decode("utf-8", errors="replace")
    if rc != 0:
        _write_reward(0.0, "D2_reconcile_sh_nonzero_exit", findings)
        return 0

    ping_ok = False
    deadline = time.monotonic() + READINESS_CEILING_SECS
    while time.monotonic() < deadline:
        prc, pout, _ = _redis_cli_over_socket("PING", timeout=3.0)
        if prc == 0 and pout.strip() == b"PONG":
            ping_ok = True
            break
        time.sleep(READINESS_POLL_SECS)
    findings["D2_ping_pong"] = ping_ok
    if not ping_ok:
        _write_reward(0.0, "D2_ping_pong_timeout", findings)
        return 0

    # --- Q1: CONFIG GET appendonly ----------------------------------------
    q1_rc, q1_out, _ = _redis_cli_over_socket("CONFIG", "GET", "appendonly",
                                              timeout=5.0)
    q1_lines = q1_out.decode("utf-8", errors="replace").splitlines()
    q1_ok = q1_rc == 0 and len(q1_lines) >= 2 \
            and q1_lines[0].strip() == "appendonly" \
            and q1_lines[1].strip() == "yes"
    findings["Q1_config_get_appendonly"] = q1_lines
    findings["Q1_ok"] = q1_ok

    # --- Q2: INFO persistence | aof_enabled ------------------------------
    q2_rc, q2_out, _ = _redis_cli_over_socket("INFO", "persistence",
                                              timeout=5.0)
    q2_txt = q2_out.decode("utf-8", errors="replace")
    q2_line = next((L for L in q2_txt.splitlines()
                    if L.startswith("aof_enabled:")), "")
    q2_ok = q2_rc == 0 and q2_line.strip() == "aof_enabled:1"
    findings["Q2_info_persistence_aof_enabled_line"] = q2_line
    findings["Q2_ok"] = q2_ok

    # --- Q3: CONFIG GET maxmemory-policy ---------------------------------
    q3_rc, q3_out, _ = _redis_cli_over_socket("CONFIG", "GET",
                                              "maxmemory-policy", timeout=5.0)
    q3_lines = q3_out.decode("utf-8", errors="replace").splitlines()
    q3_ok = q3_rc == 0 and len(q3_lines) >= 2 \
            and q3_lines[0].strip() == "maxmemory-policy" \
            and q3_lines[1].strip() == "allkeys-lru"
    findings["Q3_config_get_maxmemory_policy"] = q3_lines
    findings["Q3_ok"] = q3_ok

    # --- Q4: openssl s_client verify + fingerprint match -----------------
    q4_rc, q4_out, q4_err = _sh([
        "openssl", "s_client", "-connect", f"127.0.0.1:{TLS_PORT}",
        "-CAfile", str(TLS_DIR / "ca.crt"),
        "-verify_return_error", "-showcerts",
    ], timeout=10.0, input_bytes=b"")
    q4_txt = (q4_out + b"\n" + q4_err).decode("utf-8", errors="replace")
    q4_verify_ok = "Verify return code: 0 (ok)" in q4_txt

    q4_observed_fp, fp_log = _capture_server_cert_fingerprint()
    q4_pinned_fp = _read_pinned_fingerprint()
    q4_fp_ok = (q4_observed_fp is not None
                and q4_pinned_fp is not None
                and q4_observed_fp == q4_pinned_fp)
    q4_ok = q4_verify_ok and q4_fp_ok
    findings["Q4_verify_return_code_zero"] = q4_verify_ok
    findings["Q4_observed_fingerprint"] = q4_observed_fp
    findings["Q4_pinned_fingerprint"] = q4_pinned_fp
    findings["Q4_fingerprint_fetch_log"] = fp_log
    findings["Q4_ok"] = q4_ok

    # --- Q5: redis-cli --tls PING ----------------------------------------
    q5_rc, q5_out, _ = _sh([
        "redis-cli", "--tls", "--cacert", str(TLS_DIR / "ca.crt"),
        "-h", "127.0.0.1", "-p", str(TLS_PORT), "PING",
    ], timeout=10.0)
    q5_ok = q5_rc == 0 and q5_out.strip() == b"PONG"
    findings["Q5_redis_cli_tls_ping"] = q5_out.decode("utf-8", errors="replace").strip()
    findings["Q5_ok"] = q5_ok

    # --- Q6: mutation_tick liveness --------------------------------------
    tick_at_end = _mutation_tick_mtime()
    findings["mutation_tick_at_verifier_end"] = tick_at_end
    if tick_at_end is None:
        q6_ok = False
    elif tick_at_start is not None and tick_at_end > tick_at_start:
        q6_ok = True
    else:
        # Fall-back: file exists and its mtime is recent (within the last
        # 2 drift-cadence windows) which proves the loop is live.
        q6_ok = (time.time() - tick_at_end) < 180.0
    findings["Q6_ok"] = q6_ok

    # --- D4 composite ----------------------------------------------------
    d4_ok = q1_ok and q2_ok and q3_ok and q4_ok and q5_ok and q6_ok
    findings["D4_ok"] = d4_ok
    if not d4_ok:
        first = next((f"Q{i}" for i, ok in enumerate(
            [q1_ok, q2_ok, q3_ok, q4_ok, q5_ok, q6_ok], start=1)
            if not ok), "unknown")
        _write_reward(0.0, f"D4_first_failing_probe:{first}", findings)
        return 0

    # --- D3: runbook byte-level parse ------------------------------------
    runbook_bytes = RUNBOOK_MD.read_bytes()
    try:
        runbook_text = runbook_bytes.decode("utf-8")
    except UnicodeDecodeError:
        _write_reward(0.0, "D3_runbook_not_utf8", findings)
        return 0
    d3_ok, d3_reason, d3_extras = parse_runbook(runbook_text)
    findings["D3_ok"] = d3_ok
    findings["D3_extras"] = d3_extras
    if not d3_ok:
        _write_reward(0.0, d3_reason, findings)
        return 0

    # --- D5: shortcut pattern scan ---------------------------------------
    reconcile_bytes = RECONCILE_SH.read_bytes()
    d5_hits: list[dict] = []
    for label, pat in SHORTCUT_PATTERNS:
        for fname, blob in (("reconcile.sh", reconcile_bytes),
                            ("runbook.md", runbook_bytes)):
            m = pat.search(blob)
            if m:
                d5_hits.append({"pattern": label, "file": fname,
                                "byte_offset": m.start()})
    findings["D5_hits"] = d5_hits
    findings["D5_ok"] = not d5_hits
    if d5_hits:
        first = d5_hits[0]
        _write_reward(0.0,
                      f"D5_shortcut_pattern:{first['pattern']}:{first['file']}",
                      findings)
        return 0

    # --- D6: combined wc -l budget ---------------------------------------
    def _wc_l(b: bytes) -> int:
        n = b.count(b"\n")
        # wc -l counts trailing content without newline as an additional line
        # if the file does not end in \n; match that semantics.
        if b and not b.endswith(b"\n"):
            n += 1
        return n
    combined_lines = _wc_l(reconcile_bytes) + _wc_l(runbook_bytes)
    findings["D6_combined_lines"] = combined_lines
    findings["D6_budget"] = D6_COMBINED_LINE_BUDGET
    if combined_lines > D6_COMBINED_LINE_BUDGET:
        findings["D6_ok"] = False
        _write_reward(0.0,
                      f"D6_combined_line_count_{combined_lines}_exceeds_budget_{D6_COMBINED_LINE_BUDGET}",
                      findings)
        return 0
    findings["D6_ok"] = True

    # --- All checks pass -------------------------------------------------
    _write_reward(1.0, "all_deliverables_D1_through_D6_passed", findings)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        _write_reward(0.0, f"grader_exception:{type(exc).__name__}:{exc}")
        raise
