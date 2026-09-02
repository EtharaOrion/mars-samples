# Classify each BLOCKED thread as deadlock-cycle member or contention-only waiter

The file `/workspace/input/threaddump.txt` is a HotSpot-style Java thread dump (a `jstack -l <pid>` capture against a JVM running under load). Each thread appears as a stanza opened by a header line of the form:

```
"<Thread-Name>" #<tnum> [daemon] prio=<int> os_prio=<int> tid=<0xHEX16> nid=<0xHEX> <state-prose> [<addr>]
```

followed by an authoritative Java thread-state line of the form:

```
   java.lang.Thread.State: <STATE>[ (<prose>)]
```

where `<STATE>` is drawn from `{NEW, RUNNABLE, BLOCKED, WAITING, TIMED_WAITING, TERMINATED}`, followed by a stack trace with zero or more lock-inspection lines of the form:

```
	- waiting to lock <0xHEX16> (a <ClassName>)
	- waiting on <0xHEX16> (a <ClassName>)
	- locked <0xHEX16> (a <ClassName>)
	- parking to wait for <0xHEX16> (a <ClassName>)
```

Lock addresses always match `^0x[0-9a-f]{16}$` (16 lowercase-hex digits after `0x`).

## What to compute

A TRUE deadlock is a directed cycle in the wait-for graph over `BLOCKED` threads:

- Nodes: the set of threads whose `java.lang.Thread.State:` value is exactly `BLOCKED`.
- Edges: for each `BLOCKED` thread `T` carrying exactly one `- waiting to lock <L>` line, add edge `T -> U` where `U` is the (necessarily unique) thread that carries `- locked <L>` in its own stanza. If no such `U` exists in the dump, or the owner is a non-`BLOCKED` thread, the wait chain terminates and does NOT contribute to a cycle.
- A `BLOCKED` thread `T` is a deadlock member iff it lies on at least one directed cycle of the wait-for graph.
- All other `BLOCKED` threads are contention-only waiters.

Only the `- locked` line denotes monitor ownership. `- waiting to lock` denotes monitor-entry blocking. `- waiting on` and `- parking to wait for` denote park/wait-style semantics and MUST NOT be treated as ownership or as monitor-entry blocking.

The advisory prose in the stanza header (e.g. `waiting for monitor entry`, `runnable`, `sleeping`) is NOT authoritative — read the state exclusively from the `java.lang.Thread.State:` line.

## Output shape

Write to `/workspace/out/report.tsv` exactly the following rows, in exactly the following order, with a single tab byte (0x09) between field one and field two, and a single trailing newline byte at end of file:

```
DEADLOCKED_THREAD_COUNT<TAB><n_d>
CONTENTION_THREAD_COUNT<TAB><n_c>
DEADLOCK_LOCK<TAB><addr>       (zero or more, addresses ascending under byte-order lex)
CONTENTION_LOCK<TAB><addr>     (zero or more, addresses ascending under byte-order lex)
```

- `<n_d>` and `<n_c>` are non-negative decimal integer literals (no leading zeros except the literal `0`, no plus sign, no whitespace).
- A DEADLOCK_LOCK row is emitted per distinct lock address `L` for which at least one `- waiting to lock <L>` line appears on a stanza belonging to a deadlock member.
- A CONTENTION_LOCK row is emitted per distinct lock address `L` waited on by at least one contention-only thread AND not already emitted as DEADLOCK_LOCK.
- DEADLOCK_LOCK rows come before CONTENTION_LOCK rows; addresses inside each block are strictly ascending; no interleaving is allowed.
- No header row, no trailing blank line, no other row types, no JSON, no comma-separated form.

## Deliverable

Write your solution to `/workspace/solve.sh`. The verifier invokes `bash /workspace/solve.sh` from a shell rooted at `/workspace/` with `LC_ALL=C` and the pinned toolchain (`bash`, `coreutils`, `gawk`, `sed`, `grep`, `python3`, `diffutils`) on `PATH`. Your script must produce `/workspace/out/report.tsv` before it exits.

The graders check:

- **D1** output file existence, non-emptiness, valid UTF-8, single trailing newline;
- **D2** per-row shape (two tab-separated non-empty fields; row-type-conditional regex on field two);
- **D3** byte-identical set equality against the private reference row set;
- **D4** monotone row ordering (COUNT rows first in the fixed order, then DEADLOCK_LOCK block ascending, then CONTENTION_LOCK block ascending);
- **D5** absence of a bound shortcut pattern set inside `solve.sh` (canary tokens, holdout path references, hardcoded recital sentinels, private grounding key literals);
- **D6** total line count of `solve.sh` within a recorded budget.

## Off-limits

- Do not attempt network access; the environment is offline.
- Do not attempt to install additional apt / npm / pip packages.
- Do not reference paths under `/dataset/`, `/workspace/../solution/`, `/holdout/`, or grounding key names like `reference_row_set`, `canonical_output_form`, `per_field_schema_shape_regex_family`. D5 scans your `solve.sh` for these substrings and fires on any match.
- Do not paste any canary token of the form `FORGE_HOLDOUT_CANARY_` followed by 32 uppercase alphanumerics.
- Do not embed a hardcoded recital of the expected report bracketed by `HARDCODED_REPORT_RECITAL_BEGIN` / `_END` sentinels.
- Do not rely on any optional `Found N deadlock` epilogue at the end of the dump; the authored dump does not carry one.
