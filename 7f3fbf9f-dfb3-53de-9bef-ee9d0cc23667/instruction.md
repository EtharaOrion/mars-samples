# Extract critical npm-audit vulnerabilities into a canonical TSV

The file `/workspace/input/audits.jsonl` is a concatenated `npm audit --json` flavored stream. Each line is a single JSON object describing one advisory for one installed package. The relevant fields on every well-formed record are:

- `.package` (string) — the npm coordinate, e.g. `lodash` or `@babel/core`.
- `.version` (string) — the installed version string in semantic-version form.
- `.severity` (string) — one of `info`, `low`, `moderate`, `high`, or `critical`. Some records omit this field entirely.
- `.advisory.id` (string) — the GHSA identifier for the advisory.
- `.advisory.title` (string) — free-text summary of the vulnerability.
- `.path` (string) — the dependency resolution path in `node_modules/...` form.

Your task is to write a single canonical TSV stream to `/workspace/out/critical.tsv` that contains one row for every distinct critical vulnerability that affects a non-test dependency path.

## Canonical row format

Each output line MUST have exactly this shape, with fields separated by the tab byte (0x09):

```
<package>\t<installed_version>\t<GHSA_id>\t<dependency_path>
```

The output file MUST terminate in a single trailing newline byte.

## Filter rules

1. Only records whose `.severity` is exactly the string `"critical"` survive.
2. Records whose `.path` contains a `test` or `__tests__` path segment (at the start, in the middle, or at the end, always as a whole `/`-delimited segment) are dropped.
3. Exact duplicate rows (same package, version, GHSA id, path) collapse to a single row.

## Sort order

The output MUST be sorted lex-ascending under a stable C-locale byte-order comparator: primary key is the package name (field 1), secondary key is the installed version (field 2).

## Deliverable

Write your solution as `/workspace/solve.sh`. The verifier invokes `bash /workspace/solve.sh` from a shell rooted at `/workspace/`. Your script must produce `/workspace/out/critical.tsv` before it exits.

Your pipeline MUST include the three ordered stages `jq`, then `sed`, then `awk` (or `gawk`), joined by literal `|` operators. A collapsed single-tool implementation (for example a single `jq` expression that produces the entire output in one call) is rejected by D7 even if it otherwise satisfies D1-D4.

The graders check:

- **D1** output file existence, non-emptiness, valid UTF-8, single trailing newline;
- **D2** per-row shape (four tab-separated non-empty fields, each matching its schema-shape regex);
- **D3** byte-identical set equality against the canonicalized private reference critical vulnerability set;
- **D4** monotone non-decreasing ordering under a stable lex comparator on (field 1, field 2);
- **D5** absence of a bound shortcut pattern set inside `solve.sh` (canary tokens, holdout path references, hardcoded recital sentinels);
- **D6** total line count of `solve.sh` within a recorded budget.
- **D7** ordered pipeline structure inside `solve.sh` -- the script must contain the three pipeline stages `jq`, then `sed`, then `awk` (or `gawk`), each connected to the next by a literal `|` pipe operator (comment lines and backslash-newline continuations are folded before the check).

## Tooling

The image ships pinned `bash`, `coreutils`, `jq`, `gawk`, `sed`, `grep`, `python3`, `diffutils`, and `nodejs`. Do not attempt network access; the environment is offline. Do not attempt to install additional packages.
