# Make the commit-time lint hook actually check the code

The repository at `/app` ships a local, offline commit-time lint setup: a
scanner `linters/forbidden_token.py` that flags any line containing the banned
marker token, a pre-commit configuration `.pre-commit-config.yaml` that wires
that scanner as a `repo: local` hook, and `run_hooks.sh`, the entrypoint that
initializes a throwaway git index and runs `pre-commit run --all-files`. Running
`bash run_hooks.sh` today reports success, but it never actually inspects any
Python source: the hook is wired so that no source file is ever handed to the
scanner, so a file full of banned tokens would sail through untouched.

Repair the hook wiring so the configured hook genuinely lints the Python sources
in the repository. After your change, running the hook entrypoint over the
project must exit non-zero and print the offending token whenever any tracked
`.py` file contains the banned marker, and must exit zero when no tracked `.py`
file contains it. The scanner `linters/forbidden_token.py` and `run_hooks.sh`
already behave correctly; confine your change to the hook configuration so the
scanner is invoked on the project's Python files. Do not weaken, bypass, or
rewrite the scanner logic.
