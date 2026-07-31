import hashlib
import os
import subprocess
import sys

WHEELHOUSE = "/app/wheelhouse"
WHEEL_SHAS = {
    "alpha-1.0-py3-none-any.whl": "d7407d99748816272a1827a0be1d7e9fedf6ffcbd936e4814b1ee4e187533c36",
    "alpha-2.0-py3-none-any.whl": "78a694f71cfcaff7082d688ae8eaece1a0c3eecc6a4dd8d00906c817acdc5a63",
    "beta-1.0-py3-none-any.whl": "a82776af83a6eac438ffc7b12eaa81a57ae3f45925a18f18c0b2b09f8d048171",
    "beta-2.0-py3-none-any.whl": "9182ac46a250bb49e222611be36aaa17ab3264ec7cd224f1d3b21f56a5f833ae",
    "common-1.5-py3-none-any.whl": "aca366d2e1782c4c5561d710de03665b03643ff5c2c3ab3bdeddb58001023a61",
    "common-2.1-py3-none-any.whl": "67faf266d850c149c63513caba62b4191939be91103ea3a320b63b13fe6355c7",
}

if not os.path.isdir(WHEELHOUSE):
    print("wheelhouse directory missing (red-line)")
    sys.exit(1)

names = set(os.listdir(WHEELHOUSE))
expected = set(WHEEL_SHAS)
if names != expected:
    print("wheelhouse set changed (red-line); missing=", sorted(expected - names),
          "extra=", sorted(names - expected))
    sys.exit(1)

bad = []
for name, want in WHEEL_SHAS.items():
    got = hashlib.sha256(open(os.path.join(WHEELHOUSE, name), "rb").read()).hexdigest()
    if got != want:
        bad.append(name)
if bad:
    print("wheelhouse bytes modified (red-line):", bad)
    sys.exit(1)

venv_pip = "/app/.venv/bin/pip"
if not os.path.isfile(venv_pip):
    print("no virtualenv pip at", venv_pip)
    sys.exit(1)
pc = subprocess.run([venv_pip, "check"], capture_output=True, text=True)
if pc.returncode != 0:
    print("pip check reported broken requirements:\n" + pc.stdout + pc.stderr)
    sys.exit(1)

print("integrity ok")
sys.exit(0)
