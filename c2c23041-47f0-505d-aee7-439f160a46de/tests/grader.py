#!/usr/bin/env python3
"""Grader for nginx-mtls-forward-auth-single-service (inv-22).

Runs D1..D6 against the three agent-authored files at /workspace/ and
writes reward JSON to /logs/verifier/reward.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

NGINX_CONF   = Path(os.environ.get("NGINX_MTLS_CONF",   "/workspace/nginx.conf"))
MIME_TYPES   = Path(os.environ.get("NGINX_MTLS_MIME",   "/workspace/mime.types"))
RELOAD_SH    = Path(os.environ.get("NGINX_MTLS_RELOAD", "/workspace/reload.sh"))
ACCESS_LOG   = Path("/var/log/nginx/access.log")
REWARD_PATH  = Path(os.environ.get("REWARD_PATH", "/logs/verifier/reward.json"))

D6_COMBINED_LINE_BUDGET = 220

PKI = Path("/workspace/input/pki")
UPSTREAM_INDEX = Path("/opt/upstream/index.html")
REFERENCE_UPSTREAM_SHA256 = hashlib.sha256(UPSTREAM_INDEX.read_bytes()).hexdigest() \
    if UPSTREAM_INDEX.is_file() else None

BOUND_LOG_FIELDS = {
    "request_id", "remote_addr", "ts_iso8601", "request_method",
    "request_uri", "http_host", "status", "body_bytes_sent",
    "request_time_seconds", "ssl_client_verify", "ssl_client_s_dn",
    "http_user_agent",
}

REFERENCE_CN_REGEX = re.compile(r"^CN=svc-alpha,O=Ethara$")

BOUND_SHORTCUT_PATTERNS = [
    (re.compile(rb"FORGE_HOLDOUT_CANARY_[A-Z0-9]{32}"),        "canary_token"),
    (re.compile(rb"solution/grounding\.yaml"),                "grounding_yaml_path"),
    (re.compile(rb"solution/TRUTH\.md"),                      "truth_md_path"),
    (re.compile(rb"dataset/[0-9a-f-]{36}/(solution|tests)/"),  "dataset_holdout_path"),
    (re.compile(rb"/holdout/"),                                "holdout_slash"),
    (re.compile(rb"HARDCODED_(NGINX_CONF|EXPECTED_RESPONSE|PROBE_TRUTH_TABLE)_(BEGIN|END)"),
                                                                "hardcoded_recital_marker"),
    (re.compile(rb"reference_probe_truth_table"),              "grounding_key_truth_table"),
    (re.compile(rb"reference_log_record"),                     "grounding_key_log_record"),
    (re.compile(rb"bound_log_field_set"),                      "grounding_key_field_set"),
    (re.compile(rb"reference_upstream_observed_subject_map"),  "grounding_key_subject_map"),
    (re.compile(rb"combined_line_budget"),                     "grounding_key_line_budget"),
    (re.compile(rb"\bssl_verify_client\s+(off|optional_no_ca)\b"), "mtls_bypass"),
    (re.compile(rb"\bproxy_ssl_verify\s+off\b"),            "proxy_ssl_verify_off"),
    (re.compile(rb"\bnginx\s+-T\b"),                        "nginx_dash_T"),
    (re.compile(rb"\bcurl\s+.*(-k|--insecure)\b"),          "curl_insecure"),
    (re.compile(rb"\bapt(-get)?\s+(install|update|upgrade)\b"), "apt_install"),
    (re.compile(rb"\bpip3?\s+install\b"),                   "pip_install"),
    (re.compile(rb"\bnpm\s+install\b"),                     "npm_install"),
    (re.compile(rb"\bcargo\s+install\b"),                   "cargo_install"),
    (re.compile(rb"\bcurl\s+(https?|ftp)://"),               "curl_network"),
    (re.compile(rb"\bwget\b"),                                "wget"),
    (re.compile(rb"\bgit\s+clone\b"),                       "git_clone"),
]


def _reward(success, reason, breakdown):
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "reward": 1.0 if success else 0.0,
        "success": bool(success),
        "reason": reason,
        "breakdown": breakdown,
    }
    REWARD_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def d1_presence_and_shape():
    details = {}
    for label, p, needs_exec in [
        ("nginx_conf", NGINX_CONF, False),
        ("mime_types", MIME_TYPES, False),
        ("reload_sh",  RELOAD_SH,  True),
    ]:
        if not p.is_file():
            return False, {"failed_on": label, "path": str(p), "reason": "missing"}
        data = p.read_bytes()
        if len(data) == 0:
            return False, {"failed_on": label, "path": str(p), "reason": "empty"}
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as e:
            return False, {"failed_on": label, "path": str(p), "reason": f"invalid_utf8:{e}"}
        if needs_exec and (p.stat().st_mode & 0o100) != 0o100:
            return False, {"failed_on": label, "path": str(p), "reason": "not_owner_executable"}
        details[label] = {"size": len(data)}
    return True, details


def d5_shortcut_pattern_scan():
    hits = []
    for p in (NGINX_CONF, MIME_TYPES, RELOAD_SH):
        try:
            data = p.read_bytes()
        except OSError:
            continue
        for regex, label in BOUND_SHORTCUT_PATTERNS:
            m = regex.search(data)
            if m:
                hits.append({
                    "path": str(p),
                    "pattern": label,
                    "byte_offset": m.start(),
                    "matched_bytes": m.group().decode("utf-8", errors="replace"),
                })
    return len(hits) == 0, {"hits": hits}


def d6_combined_line_budget():
    total = 0
    per_file = {}
    for p in (NGINX_CONF, MIME_TYPES, RELOAD_SH):
        data = p.read_bytes() if p.is_file() else b""
        nl = data.count(b"\n")
        tail = 0 if data.endswith(b"\n") else (1 if data else 0)
        lc = nl + tail
        per_file[str(p)] = lc
        total += lc
    return total <= D6_COMBINED_LINE_BUDGET, {
        "combined_line_count": total,
        "budget": D6_COMBINED_LINE_BUDGET,
        "per_file": per_file,
    }


def _run(cmd, timeout=30, env=None):
    return subprocess.run(
        cmd, capture_output=True, timeout=timeout,
        env={**os.environ, **(env or {}), "LC_ALL": "C"},
    )


def _kill_nginx():
    subprocess.run(["nginx", "-s", "quit"], capture_output=True, timeout=10)
    for _ in range(15):
        r = subprocess.run(["pgrep", "-x", "nginx"], capture_output=True)
        if r.returncode != 0:
            return
        time.sleep(0.2)
    subprocess.run(["pkill", "-9", "-x", "nginx"], capture_output=True)


def d2_reload_and_bind():
    _kill_nginx()
    # rotate the access log so the D4 window is exactly the probe-induced lines
    Path("/var/log/nginx").mkdir(parents=True, exist_ok=True)
    ACCESS_LOG.write_bytes(b"")

    r = _run(["bash", str(RELOAD_SH)], timeout=60)
    if r.returncode != 0:
        return False, {"failed_on": "reload_sh_exit", "returncode": r.returncode,
                       "stderr": r.stderr.decode("utf-8", errors="replace")[:2000]}
    rt = _run(["nginx", "-t", "-c", "/etc/nginx/nginx.conf"], timeout=15)
    if rt.returncode != 0:
        return False, {"failed_on": "nginx_t_recheck", "returncode": rt.returncode,
                       "stderr": rt.stderr.decode("utf-8", errors="replace")[:2000]}
    deadline = time.time() + 5.0
    bound = False
    while time.time() < deadline:
        ss = _run(["ss", "-ltn", "sport", "=", ":443"], timeout=5)
        if b":443" in ss.stdout:
            bound = True
            break
        time.sleep(0.1)
    if not bound:
        return False, {"failed_on": "tcp_443_bind_timeout"}
    return True, {"bound": True}


def _curl(args, timeout=15):
    cmd = ["curl", "--silent", "--show-error",
           "--output", "/tmp/_probe_body",
           "--write-out", "%{http_code}\n%{redirect_url}\n",
           "--cacert", str(PKI / "server-ca.crt"),
           "--resolve", "localhost:443:127.0.0.1",
           "--resolve", "localhost:80:127.0.0.1"] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout,
                           env={**os.environ, "LC_ALL": "C"})
    except subprocess.TimeoutExpired:
        return {"exit": -1, "status": 0, "redirect": "", "body": b"", "timeout": True}
    body = Path("/tmp/_probe_body").read_bytes() if Path("/tmp/_probe_body").exists() else b""
    out = r.stdout.decode("utf-8", errors="replace").splitlines() + ["", ""]
    try:
        status = int(out[0])
    except ValueError:
        status = 0
    return {"exit": r.returncode, "status": status, "redirect": out[1],
            "body": body, "stderr": r.stderr.decode("utf-8", errors="replace")[:400]}


def _echo_upstream_subject(client_cert):
    r = _curl(["--cert", str(client_cert.with_suffix(".crt")),
               "--key",  str(client_cert.with_suffix(".key")),
               "--tlsv1.3", "https://localhost/_echo_headers"], timeout=15)
    subj = None
    if r["status"] == 200 and r["body"]:
        for line in r["body"].decode("utf-8", errors="replace").splitlines():
            if line.lower().startswith("x-verified-subject:"):
                subj = line.split(":", 1)[1].strip()
                break
    return subj


def d3_probe_matrix():
    results = {}
    clients = {
        "valid":      PKI / "clients" / "valid",
        "expired":    PKI / "clients" / "expired",
        "unknown-ca": PKI / "clients" / "unknown-ca",
        "revoked":    PKI / "clients" / "revoked",
    }
    # P1 valid GET /
    r = _curl(["--cert", str(clients["valid"].with_suffix(".crt")),
               "--key",  str(clients["valid"].with_suffix(".key")),
               "--tlsv1.3", "https://localhost/"], timeout=15)
    p1_body_sha = hashlib.sha256(r["body"]).hexdigest() if r["body"] else ""
    p1_subj = _echo_upstream_subject(clients["valid"])
    results["P1"] = {"status": r["status"], "body_sha256": p1_body_sha,
                     "upstream_observed_subject": p1_subj,
                     "expect_status": 200,
                     "expect_body_sha256": REFERENCE_UPSTREAM_SHA256,
                     "expect_subject": "CN=svc-alpha,O=Ethara"}
    # P2 valid GET /_verify -> internal-only
    r = _curl(["--cert", str(clients["valid"].with_suffix(".crt")),
               "--key",  str(clients["valid"].with_suffix(".key")),
               "--tlsv1.3", "https://localhost/_verify"], timeout=15)
    results["P2"] = {"status": r["status"], "expect_status": 404}
    # P3 expired
    r = _curl(["--cert", str(clients["expired"].with_suffix(".crt")),
               "--key",  str(clients["expired"].with_suffix(".key")),
               "--tlsv1.3", "https://localhost/"], timeout=15)
    results["P3"] = {"status": r["status"], "expect_status": [400, 495]}
    # P4 unknown-ca
    r = _curl(["--cert", str(clients["unknown-ca"].with_suffix(".crt")),
               "--key",  str(clients["unknown-ca"].with_suffix(".key")),
               "--tlsv1.3", "https://localhost/"], timeout=15)
    results["P4"] = {"status": r["status"], "expect_status": [400, 495]}
    # P5 revoked
    r = _curl(["--cert", str(clients["revoked"].with_suffix(".crt")),
               "--key",  str(clients["revoked"].with_suffix(".key")),
               "--tlsv1.3", "https://localhost/"], timeout=15)
    results["P5"] = {"status": r["status"], "expect_status": [400, 495]}
    # P6 no cert
    r = _curl(["--tlsv1.3", "https://localhost/"], timeout=15)
    results["P6"] = {"status": r["status"], "expect_status": [400, 496]}
    # P7 valid + tlsv1.2 -> refused
    r = _curl(["--cert", str(clients["valid"].with_suffix(".crt")),
               "--key",  str(clients["valid"].with_suffix(".key")),
               "--tlsv1.2", "--tls-max", "1.2", "https://localhost/"], timeout=15)
    results["P7"] = {"curl_exit": r["exit"], "status": r["status"],
                     "expect_curl_exit_nonzero": True}
    # P8 :80 -> 301
    r = _curl(["http://localhost/foo"], timeout=15)
    results["P8"] = {"status": r["status"], "redirect": r["redirect"],
                     "expect_status": 301,
                     "expect_location": "https://localhost/foo"}

    # Evaluate
    first_fail = None
    def _fail(pid, reason):
        nonlocal first_fail
        if first_fail is None:
            first_fail = {"probe": pid, "reason": reason, "observed": results[pid]}
    if results["P1"]["status"] != 200:                    _fail("P1", "status_ne_200")
    elif results["P1"]["body_sha256"] != REFERENCE_UPSTREAM_SHA256: _fail("P1", "body_sha_mismatch")
    elif results["P1"]["upstream_observed_subject"] != "CN=svc-alpha,O=Ethara":
        _fail("P1", "upstream_subject_mismatch")
    if results["P2"]["status"] != 404:                    _fail("P2", "status_ne_404")
    if results["P3"]["status"] not in (400, 495):         _fail("P3", "status_not_in_{400,495}")
    if results["P4"]["status"] not in (400, 495):         _fail("P4", "status_not_in_{400,495}")
    if results["P5"]["status"] not in (400, 495):         _fail("P5", "status_not_in_{400,495}")
    if results["P6"]["status"] not in (400, 496):         _fail("P6", "status_not_in_{400,496}")
    if results["P7"]["curl_exit"] == 0:                   _fail("P7", "tls12_not_refused")
    if results["P8"]["status"] != 301:                    _fail("P8", "status_ne_301")
    elif results["P8"]["redirect"] != "https://localhost/foo":
        _fail("P8", f"redirect_mismatch:{results['P8']['redirect']}")

    return first_fail is None, {"probes": results, "first_failing_probe": first_fail}


def d4_access_log_json():
    if not ACCESS_LOG.is_file():
        return False, {"reason": "access_log_missing", "path": str(ACCESS_LOG)}
    lines = [ln for ln in ACCESS_LOG.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    if not lines:
        return False, {"reason": "access_log_empty", "line_count": 0}
    p1_seen = False
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            return False, {"reason": "non_json_line", "line_index": i,
                           "error": str(e), "line_snippet": line[:200]}
        if not isinstance(obj, dict):
            return False, {"reason": "line_not_object", "line_index": i}
        keys = set(obj.keys())
        missing = BOUND_LOG_FIELDS - keys
        extra   = keys - BOUND_LOG_FIELDS
        if missing or extra:
            return False, {"reason": "field_set_mismatch", "line_index": i,
                           "missing": sorted(missing), "extra": sorted(extra)}
        if (obj.get("request_uri") == "/" and obj.get("ssl_client_verify") == "SUCCESS"
                and obj.get("status") == 200):
            if not REFERENCE_CN_REGEX.match(str(obj.get("ssl_client_s_dn", ""))):
                return False, {"reason": "P1_cn_mismatch", "line_index": i,
                               "observed_dn": obj.get("ssl_client_s_dn", "")}
            p1_seen = True
    if not p1_seen:
        return False, {"reason": "no_P1_success_log_record_found", "line_count": len(lines)}
    return True, {"line_count": len(lines), "p1_record_matched": True}


REASON_MAP = {
    "D1": "D1_authored_files_presence_or_shape_failed",
    "D2": "D2_reload_sh_or_nginx_recheck_or_port_bind_failed",
    "D3": "D3_probe_matrix_response_mismatch",
    "D4": "D4_access_log_json_shape_or_field_set_failed",
    "D5": "D5_bound_shortcut_pattern_matched_in_authored_files",
    "D6": "D6_combined_line_count_over_budget",
}


def main() -> int:
    breakdown = {}

    ok, det = d1_presence_and_shape()
    breakdown["D1"] = {"pass": ok, **det}
    if not ok:
        _reward(False, REASON_MAP["D1"], breakdown); return 1

    ok, det = d5_shortcut_pattern_scan()
    breakdown["D5"] = {"pass": ok, **det}
    if not ok:
        _reward(False, REASON_MAP["D5"], breakdown); return 1

    ok, det = d6_combined_line_budget()
    breakdown["D6"] = {"pass": ok, **det}
    if not ok:
        _reward(False, REASON_MAP["D6"], breakdown); return 1

    ok, det = d2_reload_and_bind()
    breakdown["D2"] = {"pass": ok, **det}
    if not ok:
        _reward(False, REASON_MAP["D2"], breakdown); return 1

    ok, det = d3_probe_matrix()
    breakdown["D3"] = {"pass": ok, **det}
    if not ok:
        _reward(False, REASON_MAP["D3"], breakdown); return 1

    ok, det = d4_access_log_json()
    breakdown["D4"] = {"pass": ok, **det}
    if not ok:
        _reward(False, REASON_MAP["D4"], breakdown); return 1

    _reward(True, "all_deliverables_passed", breakdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
