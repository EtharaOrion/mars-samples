import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

WORKSPACE = Path("/workspace")
RESPONSES_DIR = Path("/srv/https-mock/responses")

HOLDOUT_ENDPOINTS = [
    ("/probe_alpha_7f2e", "TOKEN_ALPHA_9c14b3e7\n"),
    ("/probe_beta_a3d1", "TOKEN_BETA_5f2a89d4\n"),
    ("/probe_gamma_e58c", "TOKEN_GAMMA_1b7c204e\n"),
]


def emit(reward: float, reason: str, prosecutor: dict, judge: dict) -> None:
    flat: dict = {"reward": float(reward)}
    for k, v in (prosecutor or {}).items():
        flat[f"p_{k}"] = int(v) if isinstance(v, bool) else v
    for k, v in (judge or {}).items():
        if isinstance(v, bool):
            flat[f"j_{k}"] = int(v)
        elif isinstance(v, (int, float)):
            flat[f"j_{k}"] = v
    json.dump(flat, sys.stdout)
    sys.stdout.write("\n")


def _cargo_toml_rustls_features(cargo_toml_path: Path) -> set[str] | None:
    if not cargo_toml_path.exists():
        return None
    obj = tomllib.loads(cargo_toml_path.read_text())
    deps = obj.get("dependencies", {})
    rustls = deps.get("rustls")
    if rustls is None:
        return None
    if isinstance(rustls, str):
        return set()
    if isinstance(rustls, dict):
        return set(rustls.get("features", []))
    return None


def prosecutor_check_workspace_unified() -> tuple[bool, str, dict]:
    a = _cargo_toml_rustls_features(WORKSPACE / "webhook_sender" / "Cargo.toml")
    b = _cargo_toml_rustls_features(WORKSPACE / "api_gateway" / "Cargo.toml")
    if a is None or b is None:
        return False, "D1_workspace_cargo_toml_still_conflicts", {
            "webhook_sender_rustls_features": sorted(a) if a is not None else None,
            "api_gateway_rustls_features": sorted(b) if b is not None else None,
            "note": "one or both members do not declare rustls; cannot verify unification",
        }
    if a != b:
        return False, "D1_workspace_cargo_toml_still_conflicts", {
            "webhook_sender_rustls_features": sorted(a),
            "api_gateway_rustls_features": sorted(b),
        }
    return True, "workspace_unified", {
        "webhook_sender_rustls_features": sorted(a),
        "api_gateway_rustls_features": sorted(b),
    }


def cold_start_rebuild(tmp_root: Path) -> tuple[bool, str, dict]:
    fresh_ws = tmp_root / "workspace"
    subprocess.run(
        ["cp", "-a", str(WORKSPACE), str(tmp_root)],
        check=True,
        timeout=600,
    )
    target_dir = fresh_ws / "target"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    build = subprocess.run(
        ["cargo", "build", "--release", "--workspace", "--offline"],
        cwd=str(fresh_ws),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if build.returncode != 0:
        return False, "D2_workspace_rebuild_failed", {
            "cargo_build_exit_code": build.returncode,
            "stderr_tail": build.stderr[-1500:],
        }
    return True, "workspace_rebuilt_from_agent_edits", {
        "cargo_build_exit_code": 0,
        "target_binary_path": str(fresh_ws / "target" / "release" / "target_binary"),
    }

def ensure_mock_serves(endpoints: list[tuple[str, str]]) -> None:
    for path, body in endpoints:
        target = RESPONSES_DIR / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)


def cleanup_mock_endpoints(endpoints: list[tuple[str, str]]) -> None:
    for path, _ in endpoints:
        target = RESPONSES_DIR / path.lstrip("/")
        try:
            target.unlink()
        except FileNotFoundError:
            pass


def judge_holdout_probes(target_binary: Path) -> tuple[bool, str, dict]:
    ensure_mock_serves(HOLDOUT_ENDPOINTS)

    pairs = [
        (HOLDOUT_ENDPOINTS[0], HOLDOUT_ENDPOINTS[1]),
        (HOLDOUT_ENDPOINTS[1], HOLDOUT_ENDPOINTS[2]),
        (HOLDOUT_ENDPOINTS[2], HOLDOUT_ENDPOINTS[0]),
    ]

    results = []
    try:
        for (ep1, body1), (ep2, body2) in pairs:
            expected = f"{body1.rstrip(chr(10))}\n---\n{body2.rstrip(chr(10))}"
            r = subprocess.run(
                [str(target_binary), ep1, ep2],
                capture_output=True,
                text=True,
                timeout=30,
            )
            ok = (r.returncode == 0) and (r.stdout.strip() == expected.strip())
            results.append({
                "endpoints": [ep1, ep2],
                "returncode": r.returncode,
                "stdout": r.stdout,
                "expected": expected,
                "pass": ok,
                "stderr_tail": r.stderr[-500:] if not ok else "",
            })
    finally:
        cleanup_mock_endpoints(HOLDOUT_ENDPOINTS)

    pass_count = sum(1 for x in results if x["pass"])
    if pass_count < len(pairs):
        first_fail = next(x for x in results if not x["pass"])
        if first_fail["returncode"] != 0:
            reason = "D3_target_binary_panicked_at_first_https_call"
        else:
            reason = "D4_holdout_endpoint_response_mismatch"
        return False, reason, {
            "holdout_endpoint_pass_count": pass_count,
            "holdout_endpoint_total": len(pairs),
            "holdout_endpoint_detail": results,
        }

    return True, "all_deliverables_passed", {
        "holdout_endpoint_pass_count": pass_count,
        "holdout_endpoint_total": len(pairs),
    }


def main() -> int:
    prosecutor_state = {
        "workspace_unified": False,
        "cargo_build_release_workspace_exit_code": None,
        "target_binary_exists_at_expected_path": False,
        "target_binary_runs_without_panic": False,
    }

    ok, reason, unified_detail = prosecutor_check_workspace_unified()
    prosecutor_state["workspace_unified"] = ok
    if not ok:
        emit(0.0, reason, prosecutor_state, {"holdout_endpoint_pass_count": 0, "holdout_endpoint_total": 3, "final_reward": 0.0, **unified_detail})
        return 0

    with tempfile.TemporaryDirectory(prefix="forge-judge-") as td:
        tmp_root = Path(td)
        ok, reason, build_detail = cold_start_rebuild(tmp_root)
        prosecutor_state["cargo_build_release_workspace_exit_code"] = build_detail.get("cargo_build_exit_code")
        if not ok:
            emit(0.0, reason, prosecutor_state, {"holdout_endpoint_pass_count": 0, "holdout_endpoint_total": 3, "final_reward": 0.0, **build_detail})
            return 0

        target_binary = Path(build_detail["target_binary_path"])
        prosecutor_state["target_binary_exists_at_expected_path"] = target_binary.exists()
        if not target_binary.exists():
            emit(0.0, "D2_workspace_rebuild_failed", prosecutor_state,
                 {"holdout_endpoint_pass_count": 0, "holdout_endpoint_total": 3, "final_reward": 0.0,
                  "reason_detail": "target_binary_missing_after_rebuild"})
            return 0

        ok, reason, judge_detail = judge_holdout_probes(target_binary)
        prosecutor_state["target_binary_runs_without_panic"] = ok or (reason != "D3_target_binary_panicked_at_first_https_call")
        final_reward = 1.0 if ok else 0.0
        judge_detail["final_reward"] = final_reward
        emit(final_reward, reason, prosecutor_state, judge_detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
