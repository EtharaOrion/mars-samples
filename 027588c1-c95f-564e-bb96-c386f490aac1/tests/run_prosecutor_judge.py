import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")
APP = WORKSPACE / "app"
CONSUMERS = WORKSPACE / "consumers"
PACKAGE_JSON = APP / "package.json"
SRC_INDEX_TS = APP / "src" / "index.ts"
SRC_LOADER_TS = APP / "src" / "loader.ts"
ESM_CONSUMER = CONSUMERS / "esm-consumer.mjs"
CJS_CONSUMER = CONSUMERS / "cjs-consumer.cjs"
NODE_MODULES = APP / "node_modules"
TSC_BIN = NODE_MODULES / ".bin" / "tsc"

EXPECTED_SOURCE_SHA256 = {
    "src/index.ts": "2e5f6a9a084c4365321c65a2d02ce5bbe5e6b7461333cc6a163f49ab64e89a74",
    "src/loader.ts": "e77b1a1a6ca80ed7546d1d5c1b56ab37866c8f2d9458df40dafb8d5bd9e6e2de",
}

EXPECTED_CONSUMER_SHA256 = {
    "esm-consumer.mjs": "36b76a66ffa101c1a44a9d3a505a8eef76cff404a4bc6ff384cad8961e1f32fd",
    "cjs-consumer.cjs": "7cc5b6347f9c8faac5d72cab6dc1e21b1bf5e76a2b4df7428df6622ff474e362",
}

EXPECTED_TYPESCRIPT_VERSION = "5.7.2"

EXPECTED_STDOUT = (
    "config.name=@pkg/dual\n"
    "config.ready=true\n"
    "config.seed=42\n"
    "combine=alpha::beta\n"
    "VERSION=1.0.0\n"
)

FORBIDDEN_HARDCODED_MARKERS = [
    "config.name=@pkg/dual",
    "combine=alpha::beta",
    "VERSION=1.0.0",
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
    for rel, expected_sha in EXPECTED_SOURCE_SHA256.items():
        p = APP / rel
        if not p.exists():
            return False, f"I1_source_file_missing:{rel}"
        actual = sha256_of_file(p)
        if actual != expected_sha:
            return False, f"I1_source_file_bytes_mutated:{rel}:got_{actual}_expected_{expected_sha}"
    return True, "source_bytes_unchanged"


def check_consumer_bytes_unchanged():
    for rel, expected_sha in EXPECTED_CONSUMER_SHA256.items():
        p = CONSUMERS / rel
        if not p.exists():
            return False, f"C1_consumer_file_missing:{rel}"
        actual = sha256_of_file(p)
        if actual != expected_sha:
            return False, f"C1_consumer_file_bytes_mutated:{rel}:got_{actual}_expected_{expected_sha}"
    return True, "consumer_bytes_unchanged"


def check_typescript_version_unchanged():
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


def load_package_json():
    if not PACKAGE_JSON.exists():
        return None, "P1_package_json_missing"
    try:
        raw = PACKAGE_JSON.read_text()
    except OSError as exc:
        return None, f"P1_package_json_read_failed:{exc}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"P1_package_json_not_valid_json:{exc}"
    if not isinstance(parsed, dict):
        return None, "P1_package_json_root_not_object"
    return parsed, "package_json_loaded"


def check_package_type_module(pkg):
    type_field = pkg.get("type")
    if type_field != "module":
        return False, f"P2_package_json_type_field_not_module:got_{type_field!r}"
    return True, "package_type_module"


def check_exports_dual_conditions(pkg):
    exports = pkg.get("exports")
    if not isinstance(exports, dict):
        return False, "P3_package_json_exports_not_object", None, None
    dot = exports.get(".")
    if not isinstance(dot, dict):
        return False, "P3_package_json_exports_dot_not_object", None, None
    import_target = dot.get("import")
    require_target = dot.get("require")
    if not isinstance(import_target, str) or not import_target:
        return False, "P4_exports_import_condition_missing_or_not_string", None, None
    if not isinstance(require_target, str) or not require_target:
        return False, "P5_exports_require_condition_missing_or_not_string", None, None
    if not import_target.startswith("./") or not require_target.startswith("./"):
        return False, "P6_exports_condition_targets_not_relative", None, None
    return True, "exports_dual_conditions_present", import_target, require_target


def resolve_relative(target):
    return (APP / target[2:]).resolve() if target.startswith("./") else (APP / target).resolve()


def check_import_entry_file_exists(import_target):
    p = resolve_relative(import_target)
    if not p.exists() or not p.is_file():
        return False, f"E1_esm_entry_file_missing:{import_target}"
    return True, "esm_entry_file_exists"


def check_require_entry_file_exists(require_target):
    p = resolve_relative(require_target)
    if not p.exists() or not p.is_file():
        return False, f"E2_cjs_entry_file_missing:{require_target}"
    return True, "cjs_entry_file_exists"


def check_cjs_entry_uses_dynamic_import(require_target):
    p = resolve_relative(require_target)
    try:
        text = p.read_text()
    except OSError as exc:
        return False, f"S1_cjs_entry_read_failed:{exc}"
    without_line_comments = re.sub(r"(?m)//[^\n]*", "", text)
    without_block_comments = re.sub(r"/\*.*?\*/", "", without_line_comments, flags=re.S)
    if not re.search(r"\bimport\s*\(", without_block_comments):
        return False, "S2_cjs_entry_missing_dynamic_import_call"
    for marker in FORBIDDEN_HARDCODED_MARKERS:
        if marker in text:
            return False, f"S3_cjs_entry_hardcodes_expected_output_marker:{marker!r}"
    return True, "cjs_entry_uses_dynamic_import_and_no_hardcoded_output"


def run_esm_consumer():
    if not ESM_CONSUMER.exists():
        return False, "R0_esm_consumer_script_missing", {}
    try:
        r = subprocess.run(
            ["node", str(ESM_CONSUMER)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(CONSUMERS),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"R1_esm_consumer_probe_failed:{exc}", {}
    if r.returncode != 0:
        return False, "R1_esm_consumer_returncode_nonzero", {
            "returncode": r.returncode,
            "stderr_tail": r.stderr[-800:],
            "stdout_tail": r.stdout[-800:],
        }
    if r.stdout != EXPECTED_STDOUT:
        return False, "R2_esm_consumer_stdout_bytes_mismatch", {
            "expected_bytes_repr": repr(EXPECTED_STDOUT),
            "actual_bytes_repr": repr(r.stdout),
        }
    return True, "esm_consumer_produced_expected_stdout", {}


def run_cjs_consumer():
    if not CJS_CONSUMER.exists():
        return False, "R0_cjs_consumer_script_missing", {}
    try:
        r = subprocess.run(
            ["node", str(CJS_CONSUMER)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(CONSUMERS),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"R3_cjs_consumer_probe_failed:{exc}", {}
    if r.returncode != 0:
        return False, "R3_cjs_consumer_returncode_nonzero", {
            "returncode": r.returncode,
            "stderr_tail": r.stderr[-800:],
            "stdout_tail": r.stdout[-800:],
        }
    if r.stdout != EXPECTED_STDOUT:
        return False, "R4_cjs_consumer_stdout_bytes_mismatch", {
            "expected_bytes_repr": repr(EXPECTED_STDOUT),
            "actual_bytes_repr": repr(r.stdout),
        }
    return True, "cjs_consumer_produced_expected_stdout", {}


def main():
    src_ok, src_reason = check_source_bytes_unchanged()
    if not src_ok:
        emit(0.0, src_reason, {"source_bytes_ok": False}, {"final_reward": 0.0})
        return 0

    cons_ok, cons_reason = check_consumer_bytes_unchanged()
    if not cons_ok:
        emit(0.0, cons_reason, {"source_bytes_ok": True, "consumer_bytes_ok": False}, {"final_reward": 0.0})
        return 0

    ver_ok, ver_reason = check_typescript_version_unchanged()
    if not ver_ok:
        emit(0.0, ver_reason, {"source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": False}, {"final_reward": 0.0})
        return 0

    pkg, pkg_reason = load_package_json()
    if pkg is None:
        emit(0.0, pkg_reason, {"source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True, "package_json_valid": False}, {"final_reward": 0.0})
        return 0

    type_ok, type_reason = check_package_type_module(pkg)
    if not type_ok:
        emit(0.0, type_reason, {
            "source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True,
            "package_json_valid": True, "package_type_module": False,
        }, {"final_reward": 0.0})
        return 0

    exp_ok, exp_reason, import_target, require_target = check_exports_dual_conditions(pkg)
    if not exp_ok:
        emit(0.0, exp_reason, {
            "source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True,
            "package_json_valid": True, "package_type_module": True, "exports_dual_conditions_ok": False,
        }, {"final_reward": 0.0})
        return 0

    esm_file_ok, esm_file_reason = check_import_entry_file_exists(import_target)
    if not esm_file_ok:
        emit(0.0, esm_file_reason, {
            "source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True,
            "package_json_valid": True, "package_type_module": True, "exports_dual_conditions_ok": True,
            "esm_entry_file_ok": False,
        }, {"final_reward": 0.0, "import_target": import_target})
        return 0

    cjs_file_ok, cjs_file_reason = check_require_entry_file_exists(require_target)
    if not cjs_file_ok:
        emit(0.0, cjs_file_reason, {
            "source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True,
            "package_json_valid": True, "package_type_module": True, "exports_dual_conditions_ok": True,
            "esm_entry_file_ok": True, "cjs_entry_file_ok": False,
        }, {"final_reward": 0.0, "require_target": require_target})
        return 0

    dyn_ok, dyn_reason = check_cjs_entry_uses_dynamic_import(require_target)
    if not dyn_ok:
        emit(0.0, dyn_reason, {
            "source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True,
            "package_json_valid": True, "package_type_module": True, "exports_dual_conditions_ok": True,
            "esm_entry_file_ok": True, "cjs_entry_file_ok": True, "cjs_dynamic_import_ok": False,
        }, {"final_reward": 0.0, "require_target": require_target})
        return 0

    esm_ok, esm_reason, esm_detail = run_esm_consumer()
    if not esm_ok:
        judge = {"final_reward": 0.0}
        judge.update(esm_detail)
        emit(0.0, esm_reason, {
            "source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True,
            "package_json_valid": True, "package_type_module": True, "exports_dual_conditions_ok": True,
            "esm_entry_file_ok": True, "cjs_entry_file_ok": True, "cjs_dynamic_import_ok": True,
            "esm_consumer_ok": False,
        }, judge)
        return 0

    cjs_ok, cjs_reason, cjs_detail = run_cjs_consumer()
    if not cjs_ok:
        judge = {"final_reward": 0.0}
        judge.update(cjs_detail)
        emit(0.0, cjs_reason, {
            "source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True,
            "package_json_valid": True, "package_type_module": True, "exports_dual_conditions_ok": True,
            "esm_entry_file_ok": True, "cjs_entry_file_ok": True, "cjs_dynamic_import_ok": True,
            "esm_consumer_ok": True, "cjs_consumer_ok": False,
        }, judge)
        return 0

    emit(
        1.0,
        "all_deliverables_passed",
        {
            "source_bytes_ok": True, "consumer_bytes_ok": True, "tsc_version_ok": True,
            "package_json_valid": True, "package_type_module": True, "exports_dual_conditions_ok": True,
            "esm_entry_file_ok": True, "cjs_entry_file_ok": True, "cjs_dynamic_import_ok": True,
            "esm_consumer_ok": True, "cjs_consumer_ok": True,
        },
        {"final_reward": 1.0},
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
