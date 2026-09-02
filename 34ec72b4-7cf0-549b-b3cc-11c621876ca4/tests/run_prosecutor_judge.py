import ast
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

WORKSPACE = Path("/workspace")
MYAPP_SRC = WORKSPACE / "myapp"
HELPERS_PY = MYAPP_SRC / "myapp" / "helpers.py"
CLI_PY = MYAPP_SRC / "myapp" / "cli.py"
PYPROJECT_TOML = MYAPP_SRC / "pyproject.toml"
VISIBLE_INPUT = WORKSPACE / "input.txt"
VISIBLE_OUTPUT = WORKSPACE / "output.txt"

VISIBLE_EXPECTED_RECORDS = [
    {"id": "r001", "value": "HELLO WORLD"},
    {"id": "r002", "value": "PYTHON 3.11"},
    {"id": "r003", "value": "ORJSON-OPTIONAL"},
    {"id": "r004", "value": "NORMALIZE ME"},
]

HOLDOUTS = [
    {
        "name": "holdout_alpha",
        "input_records": [
            {"id": "h001", "value": "  alpha beta  "},
            {"id": "h002", "value": "gamma"},
            {"id": "h003", "value": " Delta-Echo "},
        ],
        "expected_records": [
            {"id": "h001", "value": "ALPHA BETA"},
            {"id": "h002", "value": "GAMMA"},
            {"id": "h003", "value": "DELTA-ECHO"},
        ],
    },
    {
        "name": "holdout_mixed",
        "input_records": [
            {"id": "m001", "value": "mixed_case_HELLO"},
            {"id": "m002", "value": "   spaced   "},
            {"id": "m003", "value": " 12345 "},
            {"id": "m004", "value": "punctuation!"},
        ],
        "expected_records": [
            {"id": "m001", "value": "MIXED_CASE_HELLO"},
            {"id": "m002", "value": "SPACED"},
            {"id": "m003", "value": "12345"},
            {"id": "m004", "value": "PUNCTUATION!"},
        ],
    },
    {
        "name": "holdout_edge",
        "input_records": [
            {"id": "e001", "value": ""},
            {"id": "e002", "value": "x"},
            {"id": "e003", "value": "   "},
        ],
        "expected_records": [
            {"id": "e001", "value": ""},
            {"id": "e002", "value": "X"},
            {"id": "e003", "value": ""},
        ],
    },
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


def _ast_module_names_referenced(source_text):
    """Return a set of top-level module names imported or referenced in source."""
    names = set()
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            base = node
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                names.add(base.id)
    return names


def _ast_function_names(source_text):
    names = set()
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def _ast_calls_named(source_text, dotted_name):
    """Return True if source contains a call to the given dotted name (e.g. helpers.process_records)."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return False
    parts = dotted_name.split(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            chain = []
            while isinstance(func, ast.Attribute):
                chain.insert(0, func.attr)
                func = func.value
            if isinstance(func, ast.Name):
                chain.insert(0, func.id)
            if chain[-len(parts):] == parts:
                return True
    return False


def check_package_structure_preserved():
    """Static-check that helpers.py and cli.py still route processing through
    the intended path. This rejects stub shortcuts even when they happen to
    print correct-looking output for the visible probe."""
    if not HELPERS_PY.exists():
        return False, "I_helpers_py_missing"
    if not CLI_PY.exists():
        return False, "I_cli_py_missing"
    helpers_src = HELPERS_PY.read_text()
    cli_src = CLI_PY.read_text()

    helpers_names = _ast_module_names_referenced(helpers_src)
    helpers_funcs = _ast_function_names(helpers_src)
    cli_names = _ast_module_names_referenced(cli_src)

    if "process_records" not in helpers_funcs:
        return False, "I3_process_records_function_absent_from_helpers"

    if not ({"orjson", "json"} & helpers_names):
        return False, "I2_helpers_names_neither_orjson_nor_json_serializer"

    if "helpers" not in cli_names and "myapp" not in cli_names:
        return False, "I1_cli_no_longer_imports_helpers_module"

    if not _ast_calls_named(cli_src, "helpers.process_records"):
        return False, "I1_cli_no_longer_calls_helpers_process_records"

    return True, "package_structure_preserved"


def compare_records_bytes(actual_bytes, expected_records):
    try:
        actual = json.loads(actual_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"output_not_valid_utf8_json: {exc}"
    if not isinstance(actual, list):
        return False, f"output_not_a_json_list: got {type(actual).__name__}"
    if actual != expected_records:
        return False, f"output_records_mismatch: expected {expected_records!r} got {actual!r}"
    return True, "records_match"


def run_myapp_in_venv(venv_bin, subcmd_argv, timeout=30):
    myapp = venv_bin / "myapp"
    return subprocess.run(
        [str(myapp)] + subcmd_argv,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def cold_start_replay(tmp_root):
    venv_dir = tmp_root / "venv"
    venv.EnvBuilder(with_pip=True, clear=True, system_site_packages=True).create(str(venv_dir))
    venv_bin = venv_dir / "bin"
    pip = venv_bin / "pip"

    install = subprocess.run(
        [str(pip), "install", "--no-deps", "--no-index", "--no-build-isolation", "-e", str(MYAPP_SRC)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if install.returncode != 0:
        return False, "D2_reinstall_failed", {
            "install_returncode": install.returncode,
            "install_stderr_tail": install.stderr[-1000:],
        }

    myapp = venv_bin / "myapp"
    if not myapp.exists():
        return False, "D2_reinstall_produced_no_entry_point", {
            "reason_detail": "entry_point_script_not_generated_after_reinstall",
        }

    help_r = run_myapp_in_venv(venv_bin, ["--help"])
    if help_r.returncode != 0:
        return False, "D3_help_did_not_exit_zero", {
            "returncode": help_r.returncode,
            "stderr_tail": help_r.stderr[-1000:],
        }
    if not help_r.stdout.strip():
        return False, "D3_help_produced_no_stdout", {
            "reason_detail": "myapp_help_produced_no_stdout",
        }

    visible_output = tmp_root / "visible_output.txt"
    visible_r = run_myapp_in_venv(
        venv_bin,
        ["process", str(VISIBLE_INPUT), "--output", str(visible_output)],
    )
    if visible_r.returncode != 0:
        return False, "D4_visible_process_returncode_nonzero", {
            "returncode": visible_r.returncode,
            "stderr_tail": visible_r.stderr[-1000:],
        }
    if not visible_output.exists():
        return False, "D4_visible_process_produced_no_output_file", {
            "expected_path": str(visible_output),
        }
    visible_ok, visible_reason = compare_records_bytes(visible_output.read_bytes(), VISIBLE_EXPECTED_RECORDS)
    if not visible_ok:
        return False, "D4_visible_process_output_mismatch", {"detail": visible_reason}

    holdout_results = []
    for h in HOLDOUTS:
        input_path = tmp_root / f"{h['name']}_input.txt"
        output_path = tmp_root / f"{h['name']}_output.txt"
        input_path.write_text(json.dumps(h["input_records"]))
        r = run_myapp_in_venv(
            venv_bin,
            ["process", str(input_path), "--output", str(output_path)],
        )
        entry = {"name": h["name"], "returncode": r.returncode}
        if r.returncode != 0:
            entry["pass"] = False
            entry["reason"] = "returncode_nonzero"
            entry["stderr_tail"] = r.stderr[-500:]
        elif not output_path.exists():
            entry["pass"] = False
            entry["reason"] = "output_file_absent"
        else:
            ok, reason = compare_records_bytes(output_path.read_bytes(), h["expected_records"])
            entry["pass"] = ok
            entry["reason"] = reason
        holdout_results.append(entry)

    passed = sum(1 for h in holdout_results if h["pass"])
    if passed < len(HOLDOUTS):
        return False, "D5_holdout_output_mismatch", {
            "holdout_pass_count": passed,
            "holdout_total": len(HOLDOUTS),
            "holdout_detail": holdout_results,
        }

    return True, "all_deliverables_passed", {
        "holdout_pass_count": passed,
        "holdout_total": len(HOLDOUTS),
        "cold_start_replay_ok": True,
    }


def main():
    struct_ok, struct_reason = check_package_structure_preserved()
    if not struct_ok:
        emit(
            0.0,
            f"D1_package_structure_broken:{struct_reason}",
            {"structure_preserved": False, "help_ok": False, "process_ok": False},
            {"holdout_pass_count": 0, "holdout_total": len(HOLDOUTS), "final_reward": 0.0},
        )
        return 0

    if not PYPROJECT_TOML.exists():
        emit(
            0.0,
            "D1_pyproject_absent",
            {"structure_preserved": False, "help_ok": False, "process_ok": False},
            {"holdout_pass_count": 0, "holdout_total": len(HOLDOUTS), "final_reward": 0.0},
        )
        return 0

    with tempfile.TemporaryDirectory(prefix="forge-judge-") as td:
        tmp_root = Path(td)
        ok, reason, judge_detail = cold_start_replay(tmp_root)

    prosecutor = {
        "structure_preserved": True,
        "help_ok": reason not in ("D2_reinstall_failed", "D2_reinstall_produced_no_entry_point", "D3_help_did_not_exit_zero", "D3_help_produced_no_stdout"),
        "process_ok": ok,
    }
    final_reward = 1.0 if ok else 0.0
    judge = {
        "holdout_pass_count": judge_detail.get("holdout_pass_count", 0),
        "holdout_total": judge_detail.get("holdout_total", len(HOLDOUTS)),
        "final_reward": final_reward,
    }
    judge.update({k: v for k, v in judge_detail.items() if k not in ("holdout_pass_count", "holdout_total")})
    emit(final_reward, reason, prosecutor, judge)
    return 0


if __name__ == "__main__":
    sys.exit(main())
