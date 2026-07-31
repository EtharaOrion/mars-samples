import json
import os
import subprocess
import sys

VENV_PY = "/app/.venv/bin/python"
EXPECT = {"common": "2.1", "alpha": "2.0", "beta": "2.0"}

if not os.path.isfile(VENV_PY):
    print("no virtualenv interpreter at", VENV_PY)
    sys.exit(1)

probe = (
    "import json,alpha,beta,common;"
    "print(json.dumps({"
    "'common':common.__version__,'alpha':alpha.__version__,'beta':beta.__version__,"
    "'value':alpha.a()+beta.b()}))"
)
proc = subprocess.run([VENV_PY, "-c", probe], capture_output=True, text=True)
if proc.returncode != 0:
    print("import in venv failed:\n" + proc.stdout + proc.stderr)
    sys.exit(1)
try:
    info = json.loads(proc.stdout.strip().splitlines()[-1])
except Exception as exc:
    print("could not parse probe output:", exc, proc.stdout)
    sys.exit(1)

for pkg, want in EXPECT.items():
    got = info.get(pkg)
    if got != want:
        print("wrong version for %s: got %r expected %r" % (pkg, got, want))
        sys.exit(1)

if info.get("value") != 314:
    print("computed value mismatch: got %r expected 314" % (info.get("value"),))
    sys.exit(1)

vr = subprocess.run([VENV_PY, "/app/verify.py"], capture_output=True, text=True)
if vr.returncode != 0:
    print("verify.py exited nonzero:\n" + vr.stdout + vr.stderr)
    sys.exit(1)

print("install ok:", info)
sys.exit(0)
