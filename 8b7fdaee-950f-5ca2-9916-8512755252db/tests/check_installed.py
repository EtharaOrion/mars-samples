import glob
import json
import os
import subprocess
import sys

VENV_PY = "/app/.venv/bin/python"
WHEELHOUSE = "/app/wheelhouse"
EXPECT_VERSION = "1.4.2"
EXPECT_COMPUTE = {"7": 182}
EXPECT_WHEEL = "widgetlib-1.4.2-py3-none-any.whl"

if not os.path.isfile(VENV_PY):
    print("no virtualenv interpreter at", VENV_PY)
    sys.exit(1)

probe = (
    "import json, widgetlib;"
    "print(json.dumps({"
    "'version': widgetlib.__version__,"
    "'compute7': widgetlib.compute(7)}))"
)
proc = subprocess.run([VENV_PY, "-c", probe], capture_output=True, text=True)
if proc.returncode != 0:
    print("import widgetlib in venv failed:\n" + proc.stdout + proc.stderr)
    sys.exit(1)
try:
    info = json.loads(proc.stdout.strip().splitlines()[-1])
except Exception as exc:
    print("could not parse probe output:", exc, proc.stdout)
    sys.exit(1)

if info.get("version") != EXPECT_VERSION:
    print("wrong __version__: got %r expected %r" % (info.get("version"), EXPECT_VERSION))
    sys.exit(1)

if info.get("compute7") != EXPECT_COMPUTE["7"]:
    print("compute(7) mismatch: got %r expected %r" % (info.get("compute7"), EXPECT_COMPUTE["7"]))
    sys.exit(1)

if not os.path.isdir(WHEELHOUSE):
    print("wheelhouse directory missing at", WHEELHOUSE)
    sys.exit(1)

exact = os.path.join(WHEELHOUSE, EXPECT_WHEEL)
if not os.path.isfile(exact):
    found = glob.glob(os.path.join(WHEELHOUSE, "widgetlib-*-py3-none-any.whl"))
    print("expected built wheel %s missing in wheelhouse; found=%r" % (EXPECT_WHEEL, found))
    sys.exit(1)

print("install ok:", info)
sys.exit(0)
