# Triage a cargo-audit JSONL stream against a workspace member tree

## Inputs (read-only)

- `/workspace/input/workspace/Cargo.toml` -- workspace root manifest declaring a
  `[workspace]` table with a `members` array enumerating a pinned set of member
  crate paths (each a subdirectory of the workspace root).
- `/workspace/input/workspace/<member>/Cargo.toml` -- one per-member manifest for
  every listed member, declaring a `[package]` table with `name` and `version`, a
  `[dependencies]` table of zero or more direct runtime dependencies (each keyed
  by crate name and valued either as a version-requirement string literal or as
  an inline table with a `version` key), and optionally a `[dev-dependencies]`
  and `[build-dependencies]` table with the same shape.
- `/workspace/input/audit.jsonl` -- a UTF-8 JSONL stream, one JSON record per
  line, produced by a prior invocation of `cargo audit --json` against the
  resolved dependency tree of the workspace root at a pinned resolution time.
  Each record follows this authored envelope:

  ```json
  {
    "advisory": {
      "id": "RUSTSEC-YYYY-NNNN",
      "cvss": <float in [0.0, 10.0]>,
      "date": "YYYY-MM-DD",
      "title": <string>,
      "categories": [<string>, ...],
      "url": <string>
    },
    "package":            {"name": <string>, "version": <string>},
    "affected_versions":  [<string>, ...],
    "patched_versions":   [<string>, ...],
    "resolution_paths":   [[<direct_dep>, ..., <package_name>], ...]
  }
  ```

  `resolution_paths` is an authored augmentation of the standard cargo-audit
  envelope. Each entry is a path in the resolved dependency graph starting at a
  workspace member's direct dep and ending at the vulnerable package. An empty
  `resolution_paths` means no workspace member's dependency closure reaches this
  package. `resolution_paths` may include paths rooted at `[dev-dependencies]`
  or `[build-dependencies]` keys -- your solve MUST NOT treat those as
  qualifying direct-dep roots.
- `/workspace/input/NOW.txt` -- a single UTF-8 text line of exact shape
  `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` followed by a single trailing newline byte.
  This is the sole source of the reference "current date" your solve must
  window against. You MUST NOT read the container wall clock via `date`,
  `python3 datetime.now()`, `time.time()`, or any equivalent form; a D5 pattern
  scan over `solve.sh` will fire on such calls.

## What to compute

For every advisory record `A` in `audit.jsonl` and every workspace member `M`,
emit a row to `/workspace/out/triage.tsv` iff ALL of the following hold:

1. `A.advisory.cvss` falls in `CRITICAL` (`>= 9.0`), `HIGH` (`>= 7.0` and
   `< 9.0`), or `MEDIUM` (`>= 4.0` and `< 7.0`). Advisories at `LOW`
   (`>= 0.1` and `< 4.0`) or `NONE` (`== 0.0`) are dropped.
2. `A.advisory.date` falls in the closed 90-day trailing window ending at
   `NOW.txt` (inclusive at BOTH endpoints, i.e. an advisory dated exactly 90
   days before NOW is included and an advisory dated 91 days before is
   excluded). Compute via python3 stdlib `datetime` arithmetic over the bytes
   of `NOW.txt`.
3. Either:
   - `A.package.name` appears as a key in `M`'s `[dependencies]` table
     (regardless of any `[dev-dependencies]` or `[build-dependencies]`
     presence) -- classify as `direct`; OR
   - `A.package.name` does not appear in ANY of `M`'s
     `[dependencies]`/`[dev-dependencies]`/`[build-dependencies]` tables but at
     least one path in `A.resolution_paths` has a first element that IS a key
     in `M`'s `[dependencies]` table -- classify as `transitive`.

   If neither, drop the (advisory, member) pair.

Every qualifying pair produces exactly one row. A single advisory that hits N
distinct members produces N distinct rows with distinct field 3 values.

## Output shape

Write to `/workspace/out/triage.tsv` a UTF-8 stream terminated by exactly one
trailing newline byte, composed of zero or more rows, each row exactly three
tab-separated positional fields with a single tab byte (0x09) between fields:

```
<severity_bucket><TAB><advisory_id><TAB><join_key>
```

- `<severity_bucket>` is one of `CRITICAL`, `HIGH`, `MEDIUM` (closed set, case-
  sensitive).
- `<advisory_id>` matches `^RUSTSEC-[0-9]{4}-[0-9]{4}$` verbatim (15 bytes).
- `<join_key>` is `<member_crate_name>:<dep_kind>:<package_name>`, where
  `<member_crate_name>` is the `[package].name` field of the workspace member
  in cargo-crate-name shape `[a-z0-9][a-z0-9_-]*`, `<dep_kind>` is exactly
  `direct` or `transitive`, and `<package_name>` is the `advisory.package.name`
  literal in cargo-crate-name shape.

Rows are ordered under the bound comparator:

1. Primary: severity_rank DESCENDING, where `CRITICAL` has rank 3, `HIGH` has
   rank 2, `MEDIUM` has rank 1. All CRITICAL rows precede all HIGH rows precede
   all MEDIUM rows.
2. Secondary (within a severity bucket): advisory_id ASCENDING under byte-order
   lexicographic comparison over the 15-character advisory_id string.
3. Tertiary (within advisory_id tie): join_key ASCENDING under byte-order lex.

No header row, no trailing blank line, no other row types, no interleaving of
severity buckets.

## Deliverable

Write your solution to `/workspace/solve.sh`. The verifier invokes
`bash /workspace/solve.sh` from a shell rooted at `/workspace/` with `LC_ALL=C`
and the pinned toolchain (`bash`, `coreutils`, `gawk`, `sed`, `grep`,
`python3`, `diffutils`, `jq`, `patch`) on `PATH`. Your script must produce
`/workspace/out/triage.tsv` before it exits.

The graders check:

- **D1** output file existence, non-emptiness, valid UTF-8, single trailing newline;
- **D2** per-row shape (three tab-separated non-empty fields matching the bound
  per-field schema-shape regex family);
- **D3** byte-identical set equality against the private reference row set;
- **D4** monotone row ordering (severity_rank DESC, advisory_id ASC, join_key ASC);
- **D5** absence of a bound shortcut pattern set inside `solve.sh` (canary
  tokens, holdout path references, hardcoded recital sentinels, private
  grounding key literals, wall-clock date family, cargo mutation and network
  family);
- **D6** total line count of `solve.sh` within a recorded budget.

## Off-limits

- Do not attempt network access; the environment is offline.
- Do not attempt to install additional apt / npm / pip / cargo packages after
  image build. No `cargo update`, `cargo publish`, `cargo yank`, `cargo audit
  fetch`, `cargo install`. No `curl`, `wget`, `git clone`.
- Do not query the container wall clock via `date` (with `-d`, `-I`, `-u`, or
  `+%`), `datetime.now()`, `datetime.today()`, `date.today()`, `time.time()`,
  `time.localtime()`, or `time.gmtime()`. Read the reference date exclusively
  from `NOW.txt`.
- Do not reference paths under `/dataset/`, `/holdout/`, `solution/grounding.yaml`,
  or `solution/TRUTH.md`. D5 scans your `solve.sh` for these substrings.
- Do not paste any canary token of the form `FORGE_HOLDOUT_CANARY_` followed by
  32 uppercase alphanumerics.
- Do not embed a hardcoded recital of the expected triage bracketed by
  `HARDCODED_TRIAGE_RECITAL_BEGIN` / `_END` sentinels.
- Do not reference the private grounding key literals `reference_row_set`,
  `reference_advisory_id_set`, `reference_join_key_set`,
  `reference_severity_bucket_set`, `canonical_output_form`,
  `per_field_schema_shape_regex_family`, `row_ordering_comparator_contract`.
