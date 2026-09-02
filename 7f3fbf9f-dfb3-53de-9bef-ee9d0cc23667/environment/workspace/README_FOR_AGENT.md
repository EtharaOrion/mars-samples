# Working directory layout

You are in `/workspace/`. The relevant paths are:

- `/workspace/input/audits.jsonl` — the concatenated npm-audit-flavored JSONL corpus (read-only).
- `/workspace/out/` — the directory where you MUST write `critical.tsv`.

## What to author

Write your solution to `/workspace/solve.sh`. The verifier will invoke `bash /workspace/solve.sh` from `/workspace/` and then read `/workspace/out/critical.tsv`.

## What is graded

Your `solve.sh` and its output file are graded against six deliverables (D1-D6). See `instruction.md` for the exact contract. Briefly:

- The output must exist, be non-empty, and end in a single trailing newline (D1).
- Every row must be four tab-separated non-empty fields matching their per-field schema-shape regex (D2).
- The set of rows must match the private reference critical-vulnerability set exactly (D3).
- Rows must be sorted by (package, version) under a stable C-locale lex comparator (D4).
- `solve.sh` must not contain any of a bound shortcut pattern set - no canary tokens, no holdout path references, no hardcoded recital sentinels (D5).
- `solve.sh` line count must stay within a recorded budget (D6).
- `solve.sh` must contain the three ordered pipeline stages `jq`, then `sed`, then `awk` (or `gawk`), joined by literal `|` operators (D7).

## Toolchain

The image ships pinned `bash`, `coreutils`, `jq`, `gawk`, `sed`, `grep`, `python3`, `diffutils`, and `nodejs`. Do not attempt to install additional packages, and do not attempt network access; the environment is offline.

## Off-limits

- Do not reference paths under `/workspace/../dataset/` or `/holdout/` or `solution/grounding.yaml` or `solution/TRUTH.md`. D5 scans your `solve.sh` for these substrings and fires on any match.
- Do not paste any canary token of the form `FORGE_HOLDOUT_CANARY_` followed by 32 uppercase alphanumerics.
- Do not embed a hardcoded recital of the expected set bracketed by `HARDCODED_CRITICAL_VULN_RECITAL_BEGIN` / `_END` sentinels.
