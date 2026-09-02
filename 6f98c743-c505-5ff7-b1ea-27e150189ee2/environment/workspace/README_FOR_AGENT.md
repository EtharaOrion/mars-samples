# Working directory layout

You are in `/workspace/`. The relevant paths are:

- `/workspace/input/workspace/Cargo.toml` -- workspace root manifest.
- `/workspace/input/workspace/<member>/Cargo.toml` -- one per workspace member.
- `/workspace/input/audit.jsonl` -- pre-computed cargo-audit stream, one JSON record per line, augmented with a `resolution_paths` field.
- `/workspace/input/NOW.txt` -- pinned reference date (single line, YYYY-MM-DD, trailing newline).
- `/workspace/out/` -- the directory where you MUST write `triage.tsv`.

## What to author

Write your solution to `/workspace/solve.sh`. The verifier will invoke `bash /workspace/solve.sh` from `/workspace/` with `LC_ALL=C` and then read `/workspace/out/triage.tsv`.

## What is graded

Your `solve.sh` and its output file are graded against six deliverables (D1-D6). See `instruction.md` for the exact contract. Briefly:

- The output must exist, be non-empty, be valid UTF-8, and end in a single trailing newline (D1).
- Every row must be exactly three tab-separated non-empty fields matching a per-field schema regex (D2).
- The set of rows must match the private reference row set exactly (D3).
- Rows must be in the fixed order: severity_rank DESC, advisory_id ASC, join_key ASC, no interleaving (D4).
- `solve.sh` must not contain any of a bound shortcut pattern set (D5).
- `solve.sh` line count must stay within a recorded budget (D6).

## Toolchain

The image ships pinned `bash`, `coreutils`, `gawk`, `sed`, `grep`, `python3`, `diffutils`, `patch`, and `jq`. Do not attempt to install additional packages, and do not attempt network access; the environment is offline. `python3` includes `tomllib` in the stdlib.

## Off-limits

- Do not reference paths under `/dataset/`, `/holdout/`, `solution/grounding.yaml`, or `solution/TRUTH.md`. D5 scans your `solve.sh` for these substrings.
- Do not query the container wall clock (no `date -d`, `date -I`, `datetime.now()`, `time.time()`, etc.). Read the reference date exclusively from `NOW.txt`.
- Do not invoke `cargo` in any form. The audit stream is pre-computed and the resolution graph is materialized in each record's `resolution_paths` field. Do not fetch anything (no `curl`, `wget`, `git clone`).
- Do not paste any canary token of the form `FORGE_HOLDOUT_CANARY_` followed by 32 uppercase alphanumerics.
- Do not embed a hardcoded recital of the expected triage bracketed by `HARDCODED_TRIAGE_RECITAL_BEGIN` / `_END` sentinels.
