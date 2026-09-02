# Working directory layout

You are in `/workspace/`. The relevant paths are:

- `/workspace/input/threaddump.txt` -- the HotSpot jstack thread dump (read-only, static text).
- `/workspace/out/` -- the directory where you MUST write `report.tsv`.

## What to author

Write your solution to `/workspace/solve.sh`. The verifier will invoke `bash /workspace/solve.sh` from `/workspace/` with `LC_ALL=C` and then read `/workspace/out/report.tsv`.

## What is graded

Your `solve.sh` and its output file are graded against six deliverables (D1-D6). See `instruction.md` for the exact contract. Briefly:

- The output must exist, be non-empty, be valid UTF-8, and end in a single trailing newline (D1).
- Every row must be exactly two tab-separated non-empty fields matching a per-field schema regex (D2).
- The set of rows must match the private reference row set exactly (D3).
- Rows must be in the fixed order: COUNT rows first, then DEADLOCK_LOCK block ascending, then CONTENTION_LOCK block ascending (D4).
- `solve.sh` must not contain any of a bound shortcut pattern set (D5).
- `solve.sh` line count must stay within a recorded budget (D6).

## Toolchain

The image ships pinned `bash`, `coreutils`, `gawk`, `sed`, `grep`, `python3`, and `diffutils`. Do not attempt to install additional packages, and do not attempt network access; the environment is offline.

## Off-limits

- Do not reference paths under `/dataset/` or `/holdout/` or `solution/grounding.yaml` or `solution/TRUTH.md`. D5 scans your `solve.sh` for these substrings and fires on any match.
- Do not paste any canary token of the form `FORGE_HOLDOUT_CANARY_` followed by 32 uppercase alphanumerics.
- Do not embed a hardcoded recital of the expected report bracketed by `HARDCODED_REPORT_RECITAL_BEGIN` / `_END` sentinels.
- Do not rely on any optional `Found N deadlock` epilogue at the end of the dump; the authored dump does not carry one.
