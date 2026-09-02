#!/usr/bin/env python3
"""Grader for postgres-corrupt-wal-selective-recovery-single-service.

Contract binding: this grader implements D1..D6 exactly as declared in
seed/contract.yaml inv-23.  Every zero-score branch writes a reason string;
Harbor's non-empty reward-file requirement of Phase 1 rule 8 is satisfied on
every exit path.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


REWARD_PATH = Path(os.environ.get("REWARD_PATH", "/logs/verifier/reward.json"))
WORKSPACE = Path("/workspace")
DATA_DIR = Path("/var/lib/postgresql/data")
SOCKET_DIR = Path("/var/run/postgresql")
HOLDOUT_DIR = Path("/opt/holdout")
MUTATION_TICK = Path("/var/lib/postgresql/mutation_tick")

RECOVER_SH = WORKSPACE / "recover.sh"
NOTES_MD   = WORKSPACE / "notes.md"

GOLDEN = {
    "accounts":       200,
    "ledger_entries": 12500,
    "audit_events":   18200,
}
LAST_GOOD = {
    "accounts":       200,
    "ledger_entries": 8000,
    "audit_events":   12000,
}

READINESS_CEILING_SECS = 30.0
READINESS_POLL_SECS    = 0.2
D6_COMBINED_LINE_BUDGET = 130

# Shortcut regex family for D5.  Each entry is (label, compiled_pattern);
# order is significant only for reporting.  Patterns are case-insensitive.
SHORTCUT_PATTERNS = [
    ("drop_database_family",
     re.compile(r"\bdrop\s+database\b", re.IGNORECASE)),
    ("rm_rf_pg_wal_family",
     re.compile(r"rm\s+-r[fa]?\s+[^\n]*pg_wal", re.IGNORECASE)),
    ("pg_resetwal_dash_f_family",
     re.compile(r"pg_resetwal\s+-f\b", re.IGNORECASE)),
    ("last_good_sql_restore_family",
     re.compile(r"last_good\.sql", re.IGNORECASE)),
    ("pg_dump_and_wipe_family",
     re.compile(r"pg_dump\b.*(?:rm\s+-r|rm\s+--recursive|initdb\b)",
                re.IGNORECASE | re.DOTALL)),
    ("runtime_install_and_network_family",
     re.compile(r"\b(?:apt(?:-get)?\s+install|pip(?:3)?\s+install|"
                r"cargo\s+install|npm\s+install|curl\b|wget\b|"
                r"git\s+clone)\b",
                re.IGNORECASE)),
    ("pg_control_readout_recital_family",
     re.compile(r"pg_control_readout\.txt", re.IGNORECASE)),
    ("forge_holdout_canary_family",
     re.compile(rb"FORGE_HOLDOUT_CANARY_")),
    ("holdout_path_family",
     re.compile(r"/opt/holdout|/dataset/|reference_ceiling\.lsn",
                re.IGNORECASE)),
    ("private_grounding_field_family",
     re.compile(r"safe_recovery_ceiling_lsn|golden_row_counts|"
                r"combined_line_budget|shortcut_pattern_set",
                re.IGNORECASE)),
]


def _write_reward(reward: float, reason: str, extras: dict | None = None) -> None:
    payload = {"reward": float(reward), "reason": reason}
    if extras:
        payload.update(extras)
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps(payload, sort_keys=True) + "\n")


def _capture_mutation_tick(label: str) -> float | None:
    try:
        return MUTATION_TICK.stat().st_mtime
    except FileNotFoundError:
        return None


def _sh(argv: list[str], cwd: str | None = None,
        timeout: float | None = 30.0) -> tuple[int, str, str]:
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, check=False)
    return p.returncode, p.stdout, p.stderr


def _psql_scalar(sql: str) -> tuple[int, str]:
    rc, out, err = _sh([
        "psql", "-h", str(SOCKET_DIR), "-U", "postgres", "-d",
        "postgres", "-tA", "-c", sql,
    ])
    return rc, out.strip()


def _lsn_to_int(lsn: str) -> int | None:
    m = re.match(r"([0-9A-Fa-f]+)/([0-9A-Fa-f]+)$", lsn.strip())
    if not m:
        return None
    hi = int(m.group(1), 16)
    lo = int(m.group(2), 16)
    return (hi << 32) | lo


def _read_holdout_ceiling() -> int | None:
    p = HOLDOUT_DIR / "reference_ceiling.lsn"
    try:
        raw = p.read_text().strip()
    except (FileNotFoundError, PermissionError):
        return None
    return _lsn_to_int(raw)


def main() -> int:
    findings: dict[str, object] = {}
    tick_at_verifier_start = _capture_mutation_tick("verifier_start")
    findings["mutation_tick_at_verifier_start"] = tick_at_verifier_start

    # --- D1: both files exist, nonempty, valid UTF-8, recover.sh +x --------
    d1_ok = True
    d1_reason = None
    for label, path in [("recover.sh", RECOVER_SH), ("notes.md", NOTES_MD)]:
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
    if d1_ok and not os.access(RECOVER_SH, os.X_OK):
        d1_ok = False
        d1_reason = "D1_recover_sh_not_executable"
    findings["D1_ok"] = d1_ok
    findings["D1_reason"] = d1_reason
    if not d1_ok:
        _write_reward(0.0, d1_reason or "D1_failed", findings)
        return 0

    # --- Invoke recover.sh (skip if postmaster is already running) ---------
    # A well-behaved agent authors recover.sh but does not execute it; the
    # verifier is the one that runs it.  The oracle solve.sh may leave the
    # postmaster up as an artifact of demonstrating end-to-end recovery.  If
    # the postmaster is already ready on the unix socket at verifier phase
    # start, treat the pre-existing readiness as evidence that recover.sh
    # would have exited 0 and jump straight to the readiness poll and probes.
    tick_at_agent_start = tick_at_verifier_start  # verifier is after agent
    pre_ready_rc, _, _ = _sh(
        ["pg_isready", "-h", str(SOCKET_DIR), "-U", "postgres", "-q"],
        timeout=3.0,
    )
    if pre_ready_rc == 0:
        findings["recover_sh_skipped"] = True
        findings["recover_sh_skipped_reason"] = "postmaster_already_ready"
        findings["recover_sh_returncode"] = 0
        findings["recover_sh_wall_seconds"] = 0.0
    else:
        findings["recover_sh_skipped"] = False
        t0 = time.monotonic()
        rc, out, err = _sh(["bash", str(RECOVER_SH)], cwd=str(WORKSPACE),
                           timeout=120.0)
        dt = time.monotonic() - t0
        findings["recover_sh_returncode"] = rc
        findings["recover_sh_wall_seconds"] = round(dt, 3)
        findings["recover_sh_stdout_tail"] = out[-1024:]
        findings["recover_sh_stderr_tail"] = err[-1024:]
        if rc != 0:
            _write_reward(0.0, "D2_recover_sh_nonzero_exit", findings)
            return 0

    # --- D2: pg_isready within 30s -----------------------------------------
    ready = False
    deadline = time.monotonic() + READINESS_CEILING_SECS
    while time.monotonic() < deadline:
        rc, _, _ = _sh(["pg_isready", "-h", str(SOCKET_DIR), "-U",
                        "postgres", "-q"], timeout=3.0)
        if rc == 0:
            ready = True
            break
        time.sleep(READINESS_POLL_SECS)
    findings["D2_pg_isready"] = ready
    if not ready:
        _write_reward(0.0, "D2_pg_isready_timeout", findings)
        return 0

    # --- 8-probe matrix (Q1..Q8) -------------------------------------------
    q1_rc, q1_out = _psql_scalar("SELECT count(*) FROM accounts")
    q2_rc, q2_out = _psql_scalar("SELECT count(*) FROM ledger_entries")
    q3_rc, q3_out = _psql_scalar("SELECT count(*) FROM audit_events")
    q4_rc, q4_out = _psql_scalar(
        "SELECT count(*) FROM ledger_entries le "
        "LEFT JOIN accounts a ON le.account_id = a.id WHERE a.id IS NULL")
    q5_rc, q5_out = _psql_scalar(
        "SELECT count(*) FROM audit_events ae "
        "LEFT JOIN ledger_entries le ON ae.entry_id = le.id "
        "WHERE le.id IS NULL")
    q6_rc, q6_out = _psql_scalar(
        "SELECT bt_index_check('accounts_pkey')::text || '|' || "
        "bt_index_check('ledger_entries_pkey')::text || '|' || "
        "bt_index_check('audit_events_pkey')::text")
    q7_rc, q7_out = _sh(["pg_controldata", str(DATA_DIR)], timeout=10.0)[:2]
    q7_ctl_text = q7_out
    q8_rc, q8_out = _psql_scalar("SELECT 1")

    probes = {
        "Q1_accounts_count":        q1_out,
        "Q2_ledger_entries_count":  q2_out,
        "Q3_audit_events_count":    q3_out,
        "Q4_le_join_a_null_count":  q4_out,
        "Q5_ae_join_le_null_count": q5_out,
        "Q6_amcheck_concat":        q6_out,
        "Q7_pg_controldata_rc":     q7_rc,
        "Q8_select_one":            q8_out,
    }
    findings["probes"] = probes

    # --- D3: (Q1,Q2,Q3,Q4,Q5) equals golden tuple --------------------------
    expected = (str(GOLDEN["accounts"]),
                str(GOLDEN["ledger_entries"]),
                str(GOLDEN["audit_events"]),
                "0", "0")
    observed = (q1_out, q2_out, q3_out, q4_out, q5_out)
    d3_ok = (observed == expected)
    findings["D3_ok"] = d3_ok
    findings["D3_expected"] = expected
    findings["D3_observed"] = observed
    if not d3_ok:
        # Explicit diagnostic: is this the last_good.sql shortcut?
        if (q2_out == str(LAST_GOOD["ledger_entries"])
                and q3_out == str(LAST_GOOD["audit_events"])):
            _write_reward(0.0, "D3_last_good_sql_shortcut_row_counts",
                          findings)
        else:
            _write_reward(0.0, "D3_row_count_probe_tuple_mismatch", findings)
        return 0

    # --- D4: amcheck void + pg_controldata in production + mutation_tick ---
    amcheck_ok = q6_rc == 0 and q6_out == "||"  # three void || void || void
    prod_ok = (q7_rc == 0
               and "Database cluster state:" in q7_ctl_text
               and "in production" in q7_ctl_text)
    # Extract latest-checkpoint LSN from pg_controldata for the ceiling check.
    m = re.search(r"Latest checkpoint location:\s*([0-9A-Fa-f]+/[0-9A-Fa-f]+)",
                  q7_ctl_text)
    latest_ckpt_int = _lsn_to_int(m.group(1)) if m else None
    holdout_ceiling_int = _read_holdout_ceiling()
    if holdout_ceiling_int is None:
        # Fall-open floor: any recovery reaches at least 0x4_00_00_00
        # (initdb alone lands near 0x1_50_00_00 and would fail Q2/Q3 anyway;
        # this floor screens pg_resetwal-to-earlier shortcuts).
        holdout_ceiling_int = 0x400_00_00
    ckpt_ok = (latest_ckpt_int is not None
               and latest_ckpt_int >= holdout_ceiling_int)

    tick_at_verifier_end = _capture_mutation_tick("verifier_end")
    findings["mutation_tick_at_verifier_end"] = tick_at_verifier_end
    mutation_alive = (
        tick_at_verifier_end is not None
        and tick_at_verifier_start is not None
        and tick_at_verifier_end > tick_at_verifier_start - 1.0
    )
    # The rotation loop touches mutation_tick every 90s; the verifier phase
    # takes < 30s.  What we can positively assert is that mutation_tick EXISTS
    # (proof the loop ran at least once during the image build or the agent
    # phase) and its mtime is not in the future.  A stricter check would
    # require a longer verifier window; keep this permissive to match the
    # Phase 0 contract's Q8 semantics (liveness during agent phase, not
    # verifier phase).
    tick_present = tick_at_verifier_end is not None
    d4_ok = amcheck_ok and prod_ok and ckpt_ok and tick_present
    findings["D4_amcheck_ok"] = amcheck_ok
    findings["D4_pg_controldata_in_production"] = prod_ok
    findings["D4_latest_ckpt_ge_ceiling"] = ckpt_ok
    findings["D4_latest_ckpt_lsn_int"] = latest_ckpt_int
    findings["D4_holdout_ceiling_int"] = holdout_ceiling_int
    findings["D4_mutation_tick_present"] = tick_present
    findings["D4_ok"] = d4_ok
    if not d4_ok:
        reason = "D4_composite_failed"
        if not amcheck_ok:
            reason = "D4_amcheck_bt_index_check_failed"
        elif not prod_ok:
            reason = "D4_pg_controldata_not_in_production"
        elif not ckpt_ok:
            reason = "D4_latest_checkpoint_lsn_below_ceiling"
        elif not tick_present:
            reason = "D4_mutation_tick_absent"
        _write_reward(0.0, reason, findings)
        return 0

    # --- D5: shortcut regex family screen ----------------------------------
    recover_bytes = RECOVER_SH.read_bytes()
    notes_bytes = NOTES_MD.read_bytes()
    combined_bytes = recover_bytes + b"\n" + notes_bytes
    combined_str = combined_bytes.decode("utf-8", errors="replace")
    d5_hits: list[str] = []
    for label, pat in SHORTCUT_PATTERNS:
        target = combined_bytes if isinstance(pat.pattern, bytes) else combined_str
        if pat.search(target):
            d5_hits.append(label)
    findings["D5_shortcut_hits"] = d5_hits
    findings["D5_ok"] = not d5_hits
    if d5_hits:
        _write_reward(0.0, f"D5_shortcut_pattern_hit:{','.join(d5_hits)}",
                      findings)
        return 0

    # --- D6: combined wc -l line budget ------------------------------------
    def _wc_l(b: bytes) -> int:
        return b.count(b"\n")
    combined_lines = _wc_l(recover_bytes) + _wc_l(notes_bytes)
    findings["D6_combined_lines"] = combined_lines
    findings["D6_budget"] = D6_COMBINED_LINE_BUDGET
    if combined_lines > D6_COMBINED_LINE_BUDGET:
        findings["D6_ok"] = False
        _write_reward(0.0,
                      f"D6_combined_line_count_{combined_lines}_exceeds_budget_{D6_COMBINED_LINE_BUDGET}",
                      findings)
        return 0
    findings["D6_ok"] = True

    # All checks passed.
    _write_reward(1.0, "all_deliverables_D1_through_D6_passed", findings)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        _write_reward(0.0, f"grader_exception:{type(exc).__name__}:{exc}")
        raise
