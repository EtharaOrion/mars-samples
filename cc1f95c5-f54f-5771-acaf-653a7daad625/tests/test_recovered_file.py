import hashlib
import subprocess
from pathlib import Path

REPO = Path("/app")
TARGET = "app/core/config.py"

CORRECT_SHA = "f2342e762c1530b69af67fec229d4d60d882320cf788a9d2092cc6f1b949ff01"

BASELINE_MANIFEST = {
    ".gitignore": "833233b5ca573ebe24edf154281d5d1bb5dbcc6511260a87cca74f78ab1ec5e7",
    "README.md": "9d6943dbe822d912db35de4127b6a4a52bc515fddec05a04c90b74cd97010082",
    "app/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "app/core/REVISION": "b12df33fa2c33eb944fe73ab78ff62e6c6c562da0f27fa6077050363fbf1422e",
    "app/core/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "app/selfcheck.py": "ad8bde7599799fdb94191143f7ece8f390949f9857440ae28d110427de5267d2",
    "app/service.py": "a83dc08f46df815b021a42b0e697b56d2da62e0f0b76242575982cb47ef8bec6",
}


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=str(REPO), capture_output=True, text=True
    )


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_target_file_recovered():
    target = REPO / TARGET
    assert target.is_file(), "target file missing at %s" % TARGET
    assert _sha256(target) == CORRECT_SHA


def test_head_on_main():
    head = _git("rev-parse", "--abbrev-ref", "HEAD")
    assert head.returncode == 0
    assert head.stdout.strip() == "main"


def test_no_unrelated_tracked_change():
    listing = _git("ls-files")
    assert listing.returncode == 0
    tracked = set(listing.stdout.split())
    for path, expected in BASELINE_MANIFEST.items():
        assert path in tracked, "baseline file no longer tracked: %s" % path
        assert _sha256(REPO / path) == expected, "unrelated file changed: %s" % path
    extra = tracked - set(BASELINE_MANIFEST)
    assert extra == {TARGET}, "unexpected tracked changes: %s" % sorted(extra)
