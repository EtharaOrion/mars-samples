"""Prosecutor-and-judge grader for the fix-go-mod-replace-vendor-desync-v2 task.

Static checks (prosecutor):
  - I1 root go.mod is present.
  - I2 root go.mod still declares module example.com/myapp.
  - I3 root go.mod still carries a `replace example.com/mylib => ../mylib`
    directive (line form or block form).
  - I4 local replace target directory /workspace/mylib is present, and
    /workspace/mylib/go.mod is present.
  - I5 local target's go.mod now declares module example.com/mylib
    (agent fixed the mismatched declaration).

Runtime checks (judge, cold Go build cache):
  - D1 go mod verify exits 0 in /workspace/myapp.
  - D2 go build ./... exits 0 in /workspace/myapp.
  - D3 go test ./... exits 0 in /workspace/myapp with every test passing.

The grader writes a single JSON object to stdout and delegates final
reward calculation to Harbor's reward.json contract.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")
MYAPP_ROOT = WORKSPACE / "myapp"
MYLIB_ROOT = WORKSPACE / "mylib"
MYAPP_GOMOD = MYAPP_ROOT / "go.mod"
MYLIB_GOMOD = MYLIB_ROOT / "go.mod"

ROOT_MODULE_EXPECTED = "example.com/myapp"
REPLACED_MODULE_EXPECTED = "example.com/mylib"
REPLACE_TARGET_PATH_EXPECTED = "../mylib"
LOCAL_TARGET_MODULE_EXPECTED = "example.com/mylib"


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


def _parse_module_directive(gomod_text):
    """Return the module path from a go.mod's `module` directive, or None."""
    for raw_line in gomod_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("module "):
            parts = line.split(None, 1)
            if len(parts) == 2:
                mod = parts[1].strip()
                if mod.startswith('"') and mod.endswith('"'):
                    mod = mod[1:-1]
                return mod
    return None


_LINE_REPLACE_RE = re.compile(
    r"^\s*replace\s+(?P<from>\S+?)(?:\s+(?P<fromver>v\S+))?\s*=>\s*(?P<to>\S+?)(?:\s+(?P<tover>v\S+))?\s*(?://.*)?$",
    re.M,
)
_INBLOCK_REPLACE_RE = re.compile(
    r"^\s*(?P<from>\S+?)(?:\s+(?P<fromver>v\S+))?\s*=>\s*(?P<to>\S+?)(?:\s+(?P<tover>v\S+))?\s*(?://.*)?$",
    re.M,
)


def _has_replace_directive(gomod_text, from_mod, to_path):
    """Return True if go.mod carries `replace <from_mod> => <to_path>`
    in either the single-line form or inside a `replace ( ... )` block."""
    for m in _LINE_REPLACE_RE.finditer(gomod_text):
        if m.group("from") == from_mod and m.group("to") == to_path:
            return True

    in_block = False
    for raw_line in gomod_text.splitlines():
        line = raw_line.strip()
        if not in_block:
            if re.match(r"^replace\s*\(\s*$", line):
                in_block = True
            continue
        if line == ")":
            in_block = False
            continue
        m = _INBLOCK_REPLACE_RE.match(raw_line)
        if m and m.group("from") == from_mod and m.group("to") == to_path:
            return True
    return False


def check_invariants():
    if not MYAPP_GOMOD.exists():
        return False, "I1_root_gomod_missing"
    root_text = MYAPP_GOMOD.read_text()

    root_mod = _parse_module_directive(root_text)
    if root_mod != ROOT_MODULE_EXPECTED:
        return False, f"I2_root_module_declaration_changed_from_expected_to_{root_mod!r}"

    if not _has_replace_directive(root_text, REPLACED_MODULE_EXPECTED, REPLACE_TARGET_PATH_EXPECTED):
        return False, "I3_replace_directive_missing_or_altered"

    if not MYLIB_ROOT.is_dir():
        return False, "I4_local_replace_target_directory_missing"
    if not MYLIB_GOMOD.exists():
        return False, "I4_local_replace_target_gomod_missing"

    local_text = MYLIB_GOMOD.read_text()
    local_mod = _parse_module_directive(local_text)
    if local_mod != LOCAL_TARGET_MODULE_EXPECTED:
        return False, f"I5_local_target_module_declaration_still_{local_mod!r}"

    return True, "invariants_hold"


def run_go(cmd, cwd, timeout=180):
    env = os.environ.copy()
    env.setdefault("GOPROXY", "off")
    env.setdefault("GOSUMDB", "off")
    env.setdefault("GOFLAGS", "-mod=mod")
    env.setdefault("CGO_ENABLED", "0")
    env.setdefault("GOTOOLCHAIN", "local")
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def cold_start_replay():
    clean_r = run_go(["go", "clean", "-cache", "-testcache"], MYAPP_ROOT, timeout=60)
    if clean_r.returncode != 0:
        return False, "D0_go_clean_failed", {
            "stderr_tail": clean_r.stderr[-500:],
        }

    verify_r = run_go(["go", "mod", "verify"], MYAPP_ROOT, timeout=60)
    if verify_r.returncode != 0:
        return False, "D1_go_mod_verify_nonzero", {
            "verify_returncode": verify_r.returncode,
            "verify_stderr_tail": verify_r.stderr[-1000:],
            "verify_stdout_tail": verify_r.stdout[-500:],
        }
    verify_ok_marker = "all modules verified" in (verify_r.stdout + verify_r.stderr)

    build_r = run_go(["go", "build", "./..."], MYAPP_ROOT, timeout=180)
    if build_r.returncode != 0:
        return False, "D2_go_build_nonzero", {
            "build_returncode": build_r.returncode,
            "build_stderr_tail": build_r.stderr[-1000:],
            "build_stdout_tail": build_r.stdout[-500:],
        }

    test_r = run_go(["go", "test", "-count=1", "./..."], MYAPP_ROOT, timeout=300)
    if test_r.returncode != 0:
        return False, "D3_go_test_nonzero", {
            "test_returncode": test_r.returncode,
            "test_stdout_tail": test_r.stdout[-1000:],
            "test_stderr_tail": test_r.stderr[-500:],
        }
    test_pass_marker = "ok  \texample.com/myapp" in test_r.stdout

    return True, "all_deliverables_passed", {
        "go_mod_verify_ok": True,
        "go_mod_verify_marker_present": verify_ok_marker,
        "go_build_ok": True,
        "go_test_ok": True,
        "go_test_pass_marker_present": test_pass_marker,
    }


def main():
    struct_ok, struct_reason = check_invariants()
    if not struct_ok:
        emit(
            0.0,
            f"D0_invariant_violated:{struct_reason}",
            {
                "invariants_hold": False,
                "go_mod_verify_ok": False,
                "go_build_ok": False,
                "go_test_ok": False,
            },
            {"final_reward": 0.0},
        )
        return 0

    ok, reason, judge_detail = cold_start_replay()
    prosecutor = {
        "invariants_hold": True,
        "go_mod_verify_ok": judge_detail.get("go_mod_verify_ok", False),
        "go_build_ok": judge_detail.get("go_build_ok", False),
        "go_test_ok": judge_detail.get("go_test_ok", False),
    }
    final_reward = 1.0 if ok else 0.0
    judge = dict(judge_detail)
    judge["final_reward"] = final_reward
    emit(final_reward, reason, prosecutor, judge)
    return 0


if __name__ == "__main__":
    sys.exit(main())
