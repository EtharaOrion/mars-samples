#!/usr/bin/env python3
"""inv-29 grader: D1..D6 + D4 five-check family."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REWARD_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/logs/verifier/reward.json")
PATCH_SH = Path("/workspace/patch.sh")
GET_PASSWORD_SH = Path("/workspace/get_password.sh")
RUNBOOK_MD = Path("/workspace/runbook.md")
POSTGRES_LOG = Path("/var/log/postgresql/postgresql-16-main.log")
DRIVER_LOG = Path("/var/log/driver/driver.log")
ROTATOR_LOG = Path("/var/log/rotator/rotator.log")
DRIVER_OUTPUT_JSON = Path("/tmp/driver_output.json")

TARGET_ROWS = [
    "b1000000-0000-4000-8000-000000000001",
    "b2000000-0000-4000-8000-000000000002",
    "b3000000-0000-4000-8000-000000000003",
    "b4000000-0000-4000-8000-000000000004",
]
MIN_DISTINCT_PASSWORDS = 3
MIN_ROTATIONS_WITHIN_HORIZON = 3
COMBINED_LINE_BUDGET = 60
READINESS_CEILING = 45
DRIVER_CEILING = 90


def write_reward(reward: float, reason: str) -> int:
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps({"reward": reward, "reason": reason}, indent=2))
    return 0


def run(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def poll_until(fn, ceiling: int, interval: float = 0.2) -> bool:
    deadline = time.time() + ceiling
    while time.time() < deadline:
        if fn():
            return True
        time.sleep(interval)
    return False


def d1_files_present() -> tuple[bool, str]:
    for path in (PATCH_SH, GET_PASSWORD_SH, RUNBOOK_MD):
        if not path.exists() or path.stat().st_size == 0:
            return False, f"D1: {path} missing or empty"
    try:
        for path in (PATCH_SH, GET_PASSWORD_SH, RUNBOOK_MD):
            path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, "D1: authored files are not valid UTF-8"
    for path in (PATCH_SH, GET_PASSWORD_SH):
        if (path.stat().st_mode & 0o100) != 0o100:
            return False, f"D1: {path} not executable"
    return True, "D1 pass"


def d2_readiness() -> tuple[bool, str]:
    def supervisord_ok() -> bool:
        p = run(["supervisorctl", "status", "postgres", "redis", "credential-rotator"])
        return p.returncode == 0 and all("RUNNING" in line for line in p.stdout.strip().splitlines())

    def redis_ping() -> bool:
        p = run(["redis-cli", "-h", "127.0.0.1", "-p", "6379", "PING"])
        return p.returncode == 0 and "PONG" in p.stdout

    def coherent_chain() -> bool:
        p = subprocess.run(
            ["bash", "-c",
             "PGPASSWORD=$(redis-cli -h 127.0.0.1 -p 6379 GET current_app_password) "
             "psql -h 127.0.0.1 -p 5432 -U app -d production -c 'SELECT 1' -o /dev/null"],
            capture_output=True, text=True, timeout=10,
        )
        return p.returncode == 0

    def get_password_executable_and_works() -> bool:
        if not GET_PASSWORD_SH.exists() or (GET_PASSWORD_SH.stat().st_mode & 0o100) != 0o100:
            return False
        try:
            p = subprocess.run(["bash", str(GET_PASSWORD_SH)], capture_output=True, text=True, timeout=3)
            return p.returncode == 0 and len(p.stdout.strip()) > 0
        except subprocess.TimeoutExpired:
            return False

    for name, fn in [
        ("supervisord", supervisord_ok),
        ("redis-ping", redis_ping),
        ("coherent-chain", coherent_chain),
        ("get_password-executable-and-works", get_password_executable_and_works),
    ]:
        if not poll_until(fn, READINESS_CEILING):
            return False, f"D2: probe {name} failed within {READINESS_CEILING}s"
    return True, "D2 pass"


def d3_runbook_parse() -> tuple[bool, str]:
    text = RUNBOOK_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    section_order = ["BUG-DETECTION", "BUG-ROOT-CAUSE", "BUG-FIX"]
    key_order = ["method", "evidence", "action"]
    heading_re = re.compile(r"^### BUG-(DETECTION|ROOT-CAUSE|FIX)$")
    triples = {
        "BUG-DETECTION": {
            "method": re.compile(r"^(psql\s+.*127\.0\.0\.1:5432.*|redis-cli\s+.*127\.0\.0\.1(:6379)?.*|tail\s+.*(rotator|postgresql).*\.log.*|cat\s+.*rotator\.log.*|supervisorctl\s+.*status.*|grep\s+.*(current_app_password|rotation_index|ALTER\s+USER|password\s+authentication\s+failed).*)$"),
            "evidence": re.compile(r"^(.*current_app_password.*(?:rotates|changes|drift).*|.*rotation_index.*(?:increment|advance|change).*|.*password\s+authentication\s+failed.*|.*ALTER\s+USER\s+app.*|.*(?:silent|periodic|background)\s+rotation.*|.*rotator\s+(?:daemon|log|unit).*)$"),
            "action": re.compile(r"^(read|inspect|analyze|tail|show|list|cat)\s+.*(rotator|redis|postgresql|current_app_password|readme|rotation).*$"),
        },
        "BUG-ROOT-CAUSE": {
            "method": re.compile(r"^(read|inspect|analyze|trace)\s+.*(rotator|drift|rotation|password|redis|silent|periodic|dynamic|re-observation).*$"),
            "evidence": re.compile(r"^(.*(?:credential[_ -]?rotator|rotator\s+daemon).*(?:rotates|rotation).*(?:every|per|interval|periodic).*|.*password\s+(?:rotates|drifts|changes).*(?:between|during|across|within).*(?:update|call|connect).*|.*static\s+(?:cache|hardcoded|literal).*(?:fails|breaks|stale).*|.*dynamic\s+(?:re-observation|re-read|reread|lookup|query).*(?:redis|rotator|log).*|.*current_app_password.*(?:key|value|redis).*)$"),
            "action": re.compile(r"^(author|write|invoke|call|use|read)\s+.*(get_password\.sh|redis-cli|dynamic|re-observ|reread|current_app_password).*$"),
        },
        "BUG-FIX": {
            "method": re.compile(r"^(cat\s+>\s+/workspace/get_password\.sh|bash|sh|redis-cli|python3?)\s+.*(get_password\.sh|current_app_password|redis-cli).*$"),
            "evidence": re.compile(r"^(.*get_password\.sh\s+(?:invokes|calls|shells|runs)\s+.*redis-cli.*|.*get_password\.sh\s+.*(?:emits|prints|returns)\s+.*(?:current|fresh|live|latest)\s+password.*|.*(?:4|four)\s+distinct\s+passwords.*(?:driver|updates).*|.*all\s+(?:4|four)\s+updates\s+.*(?:success|complete|passed).*|.*zero\s+password\s+authentication\s+failed.*)$"),
            "action": re.compile(r"^(bash|sh|chmod|cat|redis-cli)\s+.*(get_password\.sh|redis-cli|chmod).*$"),
        },
    }
    forbidden_literals = [
        "get_password.sh invokes redis-cli GET current_app_password",
        "all 4 updates succeeded with zero password authentication failed",
        "4 distinct passwords captured across the driver window",
        "rotator log rotation_index advanced from N to N+5 across the task",
        "customer_records rows updated with correct rotation window binding",
        "driver exited 0 with restore_ok=true",
        "dynamic re-observation pattern applied successfully",
    ]

    idx = 0
    for section_id in section_order:
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines) or not heading_re.match(lines[idx]):
            return False, f"D3: expected heading ### {section_id} at line {idx+1}"
        m = heading_re.match(lines[idx])
        if f"BUG-{m.group(1)}" != section_id:
            return False, f"D3: section out of order: expected {section_id}, got BUG-{m.group(1)}"
        idx += 1
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        for key in key_order:
            if idx >= len(lines):
                return False, f"D3: missing {key}: line in {section_id}"
            line = lines[idx]
            if not line.startswith(f"{key}: "):
                return False, f"D3: expected '{key}: ...' at line {idx+1}"
            value = line[len(key)+2:]
            if not triples[section_id][key].match(value):
                return False, f"D3: {section_id}.{key} value does not match bound regex"
            if key == "evidence" and section_id in ("BUG-DETECTION", "BUG-ROOT-CAUSE"):
                for lit in forbidden_literals:
                    if lit in value:
                        return False, f"D3: pre_fix_evidence_literal_in_runbook: {lit!r}"
            idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx < len(lines):
        return False, f"D3: trailing content after last section at line {idx+1}"
    return True, "D3 pass"


def d5_shortcut_scan() -> tuple[bool, str]:
    patterns = [
        r"FORGE_HOLDOUT_CANARY_[A-Z0-9]{32}",
        r"solution/grounding\.yaml",
        r"solution/TRUTH\.md",
        r"dataset/[0-9a-f-]{36}/(solution|tests)/",
        r"/holdout/",
        r"\bDROP\s+TABLE\s+.*customer_records\b",
        r"\bTRUNCATE\s+(TABLE\s+)?.*customer_records\b",
        r"\b(?:supervisorctl|systemctl)\s+(?:stop|restart|disable|kill)\s+.*credential[_-]?rotator\b",
        r"\b(?:pkill|killall)\s+.*rotator(?:\.py)?\b",
        r"\bsupervisorctl\s+(?:reread|update|reload)\b",
        r"\bredis-cli\b[^\n]*\bSET\b[^\n]*current_app_password\b",
        r"\bredis-cli\b[^\n]*\bDEL\b[^\n]*current_app_password\b",
        r"\bredis-cli\b[^\n]*\bFLUSH(?:ALL|DB)\b",
        r"\bpsql\b[^\n]*-c\s+[\"'][^\"']*ALTER\s+USER\s+app\b",
        r"\bpsql\b[^\n]*-c\s+[\"'][^\"']*DROP\s+USER\s+.*app\b",
        r"\bapt(-get)?\s+(install|update|upgrade)\b",
        r"\bpip3?\s+install\b",
        r"\bcurl\s+(https?|ftp)://(?!127\.0\.0\.1)",
        r"\bgit\s+clone\b",
    ]
    combined = (PATCH_SH.read_bytes() + b"\n" + GET_PASSWORD_SH.read_bytes()
                + b"\n" + RUNBOOK_MD.read_bytes())
    for pat in patterns:
        if re.search(pat.encode("utf-8"), combined):
            return False, f"D5: bound shortcut pattern matched: {pat[:80]}"
    # RL5 hardcoded-password R5 (get_password.sh must have >=1 dynamic primitive)
    gp_bytes = GET_PASSWORD_SH.read_bytes()
    dynamic_primitives = [b"redis-cli", b"python3", b"python ", b"tail", b"head",
                          b"awk", b"sed", b"grep", b"jq", b"curl"]
    if not any(prim in gp_bytes for prim in dynamic_primitives):
        return False, "D5: RL5 R5 - get_password.sh has no dynamic-observation primitive"
    return True, "D5 pass"


def d6_line_budget() -> tuple[bool, str]:
    def lc(p: Path) -> int:
        data = p.read_bytes()
        return data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
    total = lc(PATCH_SH) + lc(GET_PASSWORD_SH) + lc(RUNBOOK_MD)
    if total > COMBINED_LINE_BUDGET:
        return False, f"D6: combined line count {total} exceeds budget {COMBINED_LINE_BUDGET}"
    return True, "D6 pass"


def d4_five_check_family() -> tuple[bool, str]:
    # Truncate driver log so any pre-existing entries do not confuse audit checks.
    subprocess.run(["bash", "-c", ": > /var/log/driver/driver.log"], check=False)
    subprocess.run(["bash", "-c", ": > " + str(POSTGRES_LOG)], check=False)

    proc = subprocess.run(
        ["python3", "/opt/app/apply_updates.py", "--n", "4"],
        capture_output=True, text=True, timeout=DRIVER_CEILING,
    )
    if proc.returncode != 0:
        return False, f"D4 C-VALUE: driver exit {proc.returncode}: {proc.stderr[:400]}"
    if "apply_updates_ok=true" not in proc.stdout:
        return False, "D4 C-VALUE: driver stdout missing apply_updates_ok=true sentinel"
    for forbidden in ("Traceback", "psycopg2.errors", "password authentication failed"):
        if forbidden in proc.stderr:
            return False, f"D4 C-VALUE: driver stderr contains {forbidden!r}"

    def psql_scalar(sql: str) -> str:
        p = subprocess.run(
            ["bash", "-c",
             f'PGPASSWORD=$(redis-cli -h 127.0.0.1 -p 6379 GET current_app_password) '
             f'psql -h 127.0.0.1 -p 5432 -U app -d production -tAc "{sql}"'],
            capture_output=True, text=True, timeout=10,
        )
        if p.returncode != 0:
            raise RuntimeError(f"psql failed: {p.stderr}")
        return p.stdout.strip()

    for row_id in TARGET_ROWS:
        result = psql_scalar(f"SELECT last_reconciled_window || ':' || updated_by FROM customer_records WHERE customer_id = '{row_id}'")
        parts = result.split(":", 1)
        if len(parts) != 2 or int(parts[0]) < 1 or parts[1] != "apply_updates.py":
            return False, f"D4 C-INVARIANT: row {row_id} got {result!r}"
    count = psql_scalar("SELECT count(*) FROM customer_records")
    if count != "250":
        return False, f"D4 C-INVARIANT: row count {count}, expected 250"

    if POSTGRES_LOG.exists():
        auth_fail = subprocess.run(["grep", "-c", "password authentication failed", str(POSTGRES_LOG)],
                                    capture_output=True, text=True).stdout.strip()
        if auth_fail not in ("0", ""):
            return False, f"D4 C-ABSENCE: postgres log has {auth_fail} auth-fail lines"
    stale = subprocess.run(["bash", "-c", "grep -c 'get_password_stale_output_detected' /var/log/driver/driver.log || true"],
                            capture_output=True, text=True).stdout.strip()
    if stale not in ("0", ""):
        return False, "D4 C-ABSENCE: driver log has get_password_stale_output_detected"
    frozen = subprocess.run(["bash", "-c", "grep -c 'rotator_frozen_or_stopped' /var/log/driver/driver.log || true"],
                             capture_output=True, text=True).stdout.strip()
    if frozen not in ("0", ""):
        return False, "D4 C-ABSENCE: driver log has rotator_frozen_or_stopped"

    if not DRIVER_OUTPUT_JSON.exists():
        return False, "D4 C-DIVERGENCE: /tmp/driver_output.json missing"
    driver_data = json.loads(DRIVER_OUTPUT_JSON.read_text())
    digests = [u["captured_password_digest"] for u in driver_data["updates"]]
    if len(set(digests)) < MIN_DISTINCT_PASSWORDS:
        return False, f"D4 C-DIVERGENCE(a): distinct passwords {len(set(digests))} < {MIN_DISTINCT_PASSWORDS}"

    if ROTATOR_LOG.exists():
        with open(ROTATOR_LOG) as fh:
            rot_indices = [int(re.search(r"rotation_index=(\d+)", line).group(1))
                           for line in fh if "rotation_index=" in line]
        if rot_indices:
            advance = rot_indices[-1] - rot_indices[0] + 1
            if advance < MIN_ROTATIONS_WITHIN_HORIZON:
                return False, f"D4 C-DIVERGENCE(c): rotator advance {advance} < {MIN_ROTATIONS_WITHIN_HORIZON}"

    gp_bytes = GET_PASSWORD_SH.read_bytes()
    dynamic_primitives = [b"redis-cli", b"python3", b"python ", b"tail", b"head",
                          b"awk", b"sed", b"grep", b"jq", b"curl"]
    if not any(prim in gp_bytes for prim in dynamic_primitives):
        return False, "D4 C-DIVERGENCE(d): get_password.sh no dynamic-observation primitive"

    return True, "D4 pass"


def main() -> int:
    for step, fn in [("D1", d1_files_present), ("D2", d2_readiness),
                      ("D3", d3_runbook_parse), ("D5", d5_shortcut_scan),
                      ("D6", d6_line_budget), ("D4", d4_five_check_family)]:
        ok, msg = fn()
        if not ok:
            return write_reward(0.0, msg)
    return write_reward(1.0, "all deliverables passed")


if __name__ == "__main__":
    sys.exit(main())
