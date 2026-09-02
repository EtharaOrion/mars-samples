GENERATED SECTION. DO NOT HAND-EDIT.

task_slug: fix-python-entrypoint-refactor-drift-v2
source_of_truth: solution/grounding.yaml
regenerated_by: solution/recompute.py

## The single most important insight

The `myapp` console script fails at invocation, not at install. `pip install -e /workspace/myapp` at container build
time completed cleanly because pip does not validate an installed package's transitive imports. The console-script shim
at `/usr/local/bin/myapp` was generated from `[project.scripts]` and its body is exactly `from myapp.cli import main;
main()`. Loading `myapp.cli` fires its top-level `from myapp import helpers`, which in turn fires `helpers.py` line 1
`import orjson`. orjson is declared in `pyproject.toml [project.optional-dependencies].perf` but is not installed in
this environment, so the import chain raises `ModuleNotFoundError: No module named 'orjson'` before `main()` gets a
chance to run and before argparse gets a chance to handle `--help`.

The trap is that the traceback's most eye-catching name is `myapp/helpers.py` (the top user-code frame), and the
bottom line names `orjson`. A naive agent reads one of those and reaches for a reflex: reinstall `myapp`, edit
`cli.main`, or `pip install orjson`. All three lose. `pip install -e` again re-runs the same broken install with the
same absent optional dependency and changes nothing. Editing `cli.main` does not touch the top-of-file import chain
that fails before `main()` runs, so the script still crashes. `pip install orjson` from a public index dies because
the container has no network egress. The correct read is that `helpers.py` unguardedly imports an *optional*
dependency that was designed to be optional, and the fix belongs at the import site: guard the import and provide
a functional stdlib fallback.

## The ideal solve, step by step

1. **Read the traceback all the way down, not just the top frame.** Open `/workspace/observed_error.txt`. The
   traceback frames descend `/usr/local/bin/myapp` -> `myapp/cli.py` -> `myapp/helpers.py` -> `import orjson`.
   The bottom line is `ModuleNotFoundError: No module named 'orjson'`. That is two levels below the eye-catching
   `myapp/helpers.py` frame. The failure origin is the `import orjson` statement at the top of `helpers.py`.

2. **Cross-check `pyproject.toml` to see how orjson was intended to be handled.** Open
   `/workspace/myapp/pyproject.toml`. Notice that `[project.optional-dependencies].perf = ["orjson>=3.9,<4"]`.
   orjson is *optional*. The package was designed to work without it, but somebody wrote the import in `helpers.py`
   as unconditional. That is the drift: the code contract and the packaging contract disagree.

3. **Confirm the container has no network.** A reflex `pip install orjson` will fail with a connection error
   because `network_mode = "none"` is bound in `task.toml`. Do not spend time on it. The fix must be an offline
   source edit, not a package install.

4. **Guard the import in `helpers.py` and add a stdlib fallback.** Edit `/workspace/myapp/myapp/helpers.py` so the
   top of the file becomes:

       try:
           import orjson
           def _dumps_bytes(obj):
               return orjson.dumps(obj)
       except ImportError:
           import json as _json_fallback
           def _dumps_bytes(obj):
               return _json_fallback.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

   Then replace `orjson.dumps(normalized)` at the bottom of `process_records` with `_dumps_bytes(normalized)`.
   Leave `_normalize_record`, `_normalize_value`, and the `process_records` signature untouched.

5. **Re-invoke `myapp --help` and `myapp process /workspace/input.txt`.** `--help` should exit 0 with usage on
   stdout, `process` should exit 0 and write JSON bytes to `/workspace/output.txt`. Because the source is editable-
   installed (`pip install -e`), the edit takes effect on the next invocation with no reinstall needed.

6. **Verify the output shape matches the normalization contract.** For the visible input records the output at
   `/workspace/output.txt` must parse as a JSON list where each record's `value` is the input's `value` after
   `strip().upper()` (strings) or unchanged (non-strings). The visible expected output is:
   [{"id": "r001", "value": "HELLO WORLD"}, {"id": "r002", "value": "PYTHON 3.11"}, {"id": "r003", "value": "ORJSON-OPTIONAL"}, {"id": "r004", "value": "NORMALIZE ME"}]

## Traps that catch agents that are not thinking carefully

- **Trap: reflex `pip install orjson`.** The traceback names orjson at the bottom line, and the trained
  response is to install it. This container has no network egress (`network_mode = "none"`). The command
  fails with a connection error and burns wall clock. Even with network, adding orjson without also declaring
  it in `pyproject.toml [project.dependencies]` would leave the package still broken under cold-start replay,
  because the verifier rebuilds from `pyproject.toml`, not from the installed environment.

- **Trap: reinstall `myapp`.** `pip install -e /workspace/myapp` completed cleanly at build time and will
  complete cleanly again. Re-running it does not add orjson, does not re-generate any missing bytes, and does
  not surface any new information. The failure is at *import* time inside the shipped package, not at install
  time.

- **Trap: edit `cli.main` signature or remove the `from myapp import helpers` line.** The top-of-file import
  chain fires when `myapp.cli` is loaded, before `main()` runs. Changing `main()` does not touch the import.
  Removing the `from myapp import helpers` line makes `myapp --help` pass but `myapp process` fails at runtime
  because `helpers.process_records` is unresolvable when the subcommand runs.

- **Trap: stub `helpers.process_records` to return `b"[]"` or hardcode output for the visible input.**
  The verifier runs holdout inputs the agent never sees. A stub that returns empty bytes fails the holdout on
  every record. A stub that hardcodes the visible output fails the holdout because the holdout records differ.
  The verifier also parses `helpers.py` with `ast` to confirm the intended serialization path is preserved and
  rejects stubs that discard both the orjson and json serializer references.

- **Trap: write a shell wrapper at `/usr/local/bin/myapp`.** The cold-start replay reinstalls the package
  in a fresh virtualenv, which regenerates the entry-point script from `pyproject.toml` and overwrites the
  wrapper. Even if the wrapper somehow survived, holdout inputs would fail because the wrapper has no way to
  compute correct normalized output for unseen records.

## The one route that satisfies every checker

Path b (guarded import with functional stdlib fallback in `helpers.py`) is the canonical fix. It preserves the
import chain the package was designed around, works offline, produces byte-identical JSON output to orjson for
the record shape the CLI handles, and survives cold-start replay because the source edit is picked up on the
next `pip install -e` from the edited `helpers.py`. Path a (`pip install orjson`) is only viable with network
egress and is not the route this task grades against.

### Canary tokens planted in this file
- forge_canary_a: FORGE_HOLDOUT_CANARY_5DDE55F921B68068A698FDB6170A798A
- forge_canary_b_reference: FORGE_HOLDOUT_CANARY_71AE654D5B83FDCB3B22D9CA02ABBF90
