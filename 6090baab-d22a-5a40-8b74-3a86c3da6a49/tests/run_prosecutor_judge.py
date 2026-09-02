import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")
APP = WORKSPACE / "app"
TSCONFIG = APP / "tsconfig.json"
PACKAGE_JSON = APP / "package.json"
SRC_INDEX_TS = APP / "src" / "index.ts"
SRC_GREET_TS = APP / "src" / "greet.ts"
SRC_FAREWELL_TS = APP / "src" / "farewell.ts"
DIST = APP / "dist"
DIST_INDEX_JS = DIST / "index.js"
NODE_MODULES = APP / "node_modules"
TSC_BIN = NODE_MODULES / ".bin" / "tsc"

EXPECTED_SOURCE_SHA256 = {
    "package.json": "5a868b8a2b3cfc703e1e99dd6adc87979a00ad1dd8b08597fd6311d345fad8d0",
    "src/index.ts": "1dbc6460131acd49ba893ab582a8b44a41f81bdcea3787d369d693349d4a2138",
    "src/greet.ts": "ddadb22209a4466c1f4c6075e56c0317cfe9a29fed48c6dacdb3241447368efc",
    "src/farewell.ts": "8f1e67b3f0fac8ccc06877b5fc89a79109ed56f0991585670cfc32473cb4f207",
}

EXPECTED_TYPESCRIPT_VERSION = "5.7.2"

EXPECTED_STDOUT = "Hello, Mars!\nGoodbye, Mars.\n"

FORBIDDEN_NODE_MODULES = [
    "ts-node",
    "tsx",
    "tsconfig-paths",
    "tsc-alias",
    "esbuild",
    "esbuild-register",
    "swc",
    "@swc/core",
    "@swc-node/register",
    "@esbuild-kit/esm-loader",
    "@esbuild-kit/cjs-loader",
    "bun",
    "deno",
]


def emit(reward, reason, prosecutor, judge):
    flat = {"reward": float(reward), "reason": reason}
    for k, v in (prosecutor or {}).items():
        flat[f"p_{k}"] = int(v) if isinstance(v, bool) else v
    for k, v in (judge or {}).items():
        if isinstance(v, bool):
            flat[f"j_{k}"] = int(v)
        elif isinstance(v, (int, float, str)):
            flat[f"j_{k}"] = v
        else:
            flat[f"j_{k}"] = repr(v)
    json.dump(flat, sys.stdout)
    sys.stdout.write("\n")


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_source_bytes_unchanged():
    """Every file listed in EXPECTED_SOURCE_SHA256 must exist and hash to the pinned digest."""
    for rel, expected_sha in EXPECTED_SOURCE_SHA256.items():
        p = APP / rel
        if not p.exists():
            return False, f"I1_source_file_missing:{rel}"
        actual = sha256_of_file(p)
        if actual != expected_sha:
            return False, f"I1_source_file_bytes_mutated:{rel}:got_{actual}_expected_{expected_sha}"
    return True, "source_bytes_unchanged"


def check_no_forbidden_node_modules():
    """The agent MUST NOT install any runtime shim, bundler, or ts loader package."""
    if not NODE_MODULES.exists():
        return False, "I2_node_modules_missing"
    for name in FORBIDDEN_NODE_MODULES:
        candidate = NODE_MODULES / name
        if candidate.exists():
            return False, f"I2_forbidden_runtime_shim_installed:{name}"
    return True, "no_forbidden_node_modules"


def check_typescript_version_unchanged():
    """tsc --version must still name the pinned TypeScript version."""
    if not TSC_BIN.exists():
        return False, "I3_tsc_binary_missing"
    try:
        r = subprocess.run(
            [str(TSC_BIN), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"I3_tsc_version_probe_failed:{exc}"
    if r.returncode != 0:
        return False, f"I3_tsc_version_probe_returncode_nonzero:{r.returncode}"
    version_line = (r.stdout + r.stderr).strip()
    if EXPECTED_TYPESCRIPT_VERSION not in version_line:
        return False, f"I3_tsc_version_drift:got_{version_line!r}_expected_contains_{EXPECTED_TYPESCRIPT_VERSION!r}"
    return True, "typescript_version_unchanged"


def load_tsconfig_object():
    """Parse tsconfig.json as JSON (rejecting comments/trailing commas because JSON5 is a foot-gun here)."""
    if not TSCONFIG.exists():
        return None, "T1_tsconfig_json_missing"
    try:
        raw = TSCONFIG.read_text()
    except OSError as exc:
        return None, f"T1_tsconfig_json_read_failed:{exc}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"T1_tsconfig_json_not_valid_json:{exc}"
    if not isinstance(parsed, dict):
        return None, "T1_tsconfig_json_root_not_object"
    return parsed, "tsconfig_loaded"


def check_tsconfig_bundler_binding(cfg):
    """The compilerOptions.moduleResolution field MUST resolve to bundler (case-insensitive), and noEmit MUST NOT be true."""
    compiler_options = cfg.get("compilerOptions")
    if not isinstance(compiler_options, dict):
        return False, "T2_tsconfig_missing_compilerOptions_object"
    mr = compiler_options.get("moduleResolution")
    if mr is None:
        return False, "T2_tsconfig_moduleResolution_not_set"
    if not isinstance(mr, str):
        return False, f"T2_tsconfig_moduleResolution_not_a_string:got_{type(mr).__name__}"
    if mr.lower() != "bundler":
        return False, f"T2_tsconfig_moduleResolution_not_bundler:got_{mr!r}"
    no_emit = compiler_options.get("noEmit", False)
    if no_emit is True:
        return False, "T3_tsconfig_noEmit_still_true_no_dist_will_be_emitted"
    return True, "tsconfig_moduleResolution_bundler_and_noEmit_off"


def run_tsc_noemit():
    """tsc --noEmit under the agent's tsconfig must exit 0 with zero stderr diagnostics."""
    if not TSC_BIN.exists():
        return False, "E1_tsc_binary_missing_for_noemit_check", {}
    try:
        r = subprocess.run(
            [str(TSC_BIN), "--project", str(TSCONFIG), "--noEmit"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(APP),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"E1_tsc_noemit_probe_failed:{exc}", {}
    if r.returncode != 0:
        return False, "E1_tsc_noemit_returncode_nonzero", {
            "returncode": r.returncode,
            "stderr_tail": r.stderr[-800:],
            "stdout_tail": r.stdout[-800:],
        }
    combined = (r.stdout or "") + (r.stderr or "")
    if re.search(r"\berror TS\d+", combined):
        return False, "E1_tsc_noemit_reported_diagnostics", {
            "stdout_tail": r.stdout[-800:],
            "stderr_tail": r.stderr[-800:],
        }
    return True, "tsc_noemit_clean", {}


def run_tsc_emit():
    """tsc (no --noEmit) must succeed and populate dist/ with index.js at minimum."""
    if not TSC_BIN.exists():
        return False, "E2_tsc_binary_missing_for_emit", {}
    try:
        if DIST.exists():
            for child in list(DIST.rglob("*")):
                if child.is_file():
                    try:
                        child.unlink()
                    except OSError:
                        pass
    except OSError:
        pass
    try:
        r = subprocess.run(
            [str(TSC_BIN), "--project", str(TSCONFIG)],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(APP),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"E2_tsc_emit_probe_failed:{exc}", {}
    if r.returncode != 0:
        return False, "E2_tsc_emit_returncode_nonzero", {
            "returncode": r.returncode,
            "stderr_tail": r.stderr[-800:],
            "stdout_tail": r.stdout[-800:],
        }
    if not DIST_INDEX_JS.exists():
        return False, "E2_tsc_emit_produced_no_dist_index_js", {
            "expected_path": str(DIST_INDEX_JS),
            "dist_children": sorted([str(p.relative_to(APP)) for p in DIST.rglob("*") if p.is_file()]) if DIST.exists() else [],
        }
    return True, "tsc_emit_succeeded", {}


def run_node_index():
    """node dist/index.js must exit 0 and print exactly the two expected lines."""
    if not DIST_INDEX_JS.exists():
        return False, "R1_dist_index_js_missing_before_node_run", {}
    try:
        r = subprocess.run(
            ["node", str(DIST_INDEX_JS)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(APP),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"R1_node_probe_failed:{exc}", {}
    if r.returncode != 0:
        return False, "R1_node_returncode_nonzero", {
            "returncode": r.returncode,
            "stderr_tail": r.stderr[-800:],
            "stdout_tail": r.stdout[-800:],
        }
    if r.stdout != EXPECTED_STDOUT:
        return False, "R2_node_stdout_bytes_mismatch", {
            "expected_bytes_repr": repr(EXPECTED_STDOUT),
            "actual_bytes_repr": repr(r.stdout),
        }
    return True, "node_index_produced_expected_stdout", {}


def main():
    src_ok, src_reason = check_source_bytes_unchanged()
    if not src_ok:
        emit(
            0.0,
            src_reason,
            {"source_bytes_ok": False, "tsc_noemit_ok": False, "tsc_emit_ok": False, "node_run_ok": False},
            {"final_reward": 0.0},
        )
        return 0

    mods_ok, mods_reason = check_no_forbidden_node_modules()
    if not mods_ok:
        emit(
            0.0,
            mods_reason,
            {"source_bytes_ok": True, "node_modules_ok": False},
            {"final_reward": 0.0},
        )
        return 0

    ver_ok, ver_reason = check_typescript_version_unchanged()
    if not ver_ok:
        emit(
            0.0,
            ver_reason,
            {"source_bytes_ok": True, "node_modules_ok": True, "tsc_version_ok": False},
            {"final_reward": 0.0},
        )
        return 0

    cfg, cfg_reason = load_tsconfig_object()
    if cfg is None:
        emit(
            0.0,
            cfg_reason,
            {"source_bytes_ok": True, "node_modules_ok": True, "tsc_version_ok": True, "tsconfig_valid": False},
            {"final_reward": 0.0},
        )
        return 0

    bind_ok, bind_reason = check_tsconfig_bundler_binding(cfg)
    if not bind_ok:
        emit(
            0.0,
            bind_reason,
            {
                "source_bytes_ok": True,
                "node_modules_ok": True,
                "tsc_version_ok": True,
                "tsconfig_valid": True,
                "tsconfig_bundler_binding_ok": False,
            },
            {"final_reward": 0.0},
        )
        return 0

    noemit_ok, noemit_reason, noemit_detail = run_tsc_noemit()
    if not noemit_ok:
        judge = {"final_reward": 0.0}
        judge.update(noemit_detail)
        emit(
            0.0,
            noemit_reason,
            {
                "source_bytes_ok": True,
                "node_modules_ok": True,
                "tsc_version_ok": True,
                "tsconfig_valid": True,
                "tsconfig_bundler_binding_ok": True,
                "tsc_noemit_ok": False,
            },
            judge,
        )
        return 0

    emit_ok, emit_reason, emit_detail = run_tsc_emit()
    if not emit_ok:
        judge = {"final_reward": 0.0}
        judge.update(emit_detail)
        emit(
            0.0,
            emit_reason,
            {
                "source_bytes_ok": True,
                "node_modules_ok": True,
                "tsc_version_ok": True,
                "tsconfig_valid": True,
                "tsconfig_bundler_binding_ok": True,
                "tsc_noemit_ok": True,
                "tsc_emit_ok": False,
            },
            judge,
        )
        return 0

    node_ok, node_reason, node_detail = run_node_index()
    if not node_ok:
        judge = {"final_reward": 0.0}
        judge.update(node_detail)
        emit(
            0.0,
            node_reason,
            {
                "source_bytes_ok": True,
                "node_modules_ok": True,
                "tsc_version_ok": True,
                "tsconfig_valid": True,
                "tsconfig_bundler_binding_ok": True,
                "tsc_noemit_ok": True,
                "tsc_emit_ok": True,
                "node_run_ok": False,
            },
            judge,
        )
        return 0

    emit(
        1.0,
        "all_deliverables_passed",
        {
            "source_bytes_ok": True,
            "node_modules_ok": True,
            "tsc_version_ok": True,
            "tsconfig_valid": True,
            "tsconfig_bundler_binding_ok": True,
            "tsc_noemit_ok": True,
            "tsc_emit_ok": True,
            "node_run_ok": True,
        },
        {"final_reward": 1.0},
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
