# Classify each BLOCKED thread as deadlock-cycle member or contention-only waiter

Canary A: FORGE_HOLDOUT_CANARY_63DC9F84097F538927A69BDB9C266271
Canary B: FORGE_HOLDOUT_CANARY_BD33665C6088A5E383EFBC0CAB0413FE

## The single most important insight

The lever this task turns on is that a JVM under heavy load looks nearly identical whether it is holding a true Java-level deadlock or is merely suffering pathological contention. In both cases `jstack` shows many `BLOCKED` threads, each carrying a `- waiting to lock <0xHEX16>` frame near the top of its stack. The difference is invisible to any surface-level string match: a true deadlock is a directed cycle in the wait-for graph (thread A waits for B's monitor, B waits for A's monitor, possibly with more threads in between), while a contention pileup is a fan-in tree where many threads wait for a single monitor whose owner is either `RUNNABLE` and doing work, or is not represented as a graph node at all. You cannot solve this task by counting `BLOCKED` threads, by regex-scanning for a `Found N Java-level deadlock(s):` epilogue (this dump omits it), or by assuming that every `- waiting to lock` frame implies participation in a deadlock. You must reconstruct the wait-for graph over `BLOCKED` threads only, resolve every waited-for address to the thread whose own stanza carries the matching `- locked <addr>` frame, and run cycle detection to separate cycle members from acyclic waiters.

The second insight is that `jstack -l` publishes the authoritative thread state in exactly one place: the `   java.lang.Thread.State:` line immediately below each stanza header. The header itself carries advisory prose like `waiting for monitor entry`, `runnable`, or `sleeping` that is easy to `grep` for but is not authoritative — a thread whose header prose reads `waiting for monitor entry` may have transitioned by the time the dump was flushed, and a `BLOCKED` thread whose header text lacks that phrase will be missed. A solver that keys `BLOCKED`-hood on header substrings will silently misclassify threads whose header prose disagrees with the authoritative state.

Thread names in this fixture are deliberately opaque (Worker-0001 through Worker-0015) and stanza order interleaves BLOCKED and non-BLOCKED positions. A solver that partitions threads by name prefix or by stanza position will misclassify every thread. Lock addresses in this fixture share a single 0x00007fabc4 prefix range; deadlock-cycle monitors and contention monitors have interleaved suffixes within that range, so a solver that partitions monitors by address prefix will misclassify every lock.

## The ideal solve, step by step

1. **Parse the dump into per-thread stanzas keyed by `tid=`.** Walk `/workspace/input/threaddump.txt` with a stateful parser (a `gawk` script anchored on `/^"[^"]+"[[:space:]]+#[0-9]+/` for the stanza header is the natural fit). For each stanza collect four fields: the `tid=0x…` from the header, the state token from the `java.lang.Thread.State:` line below, the single `- waiting to lock <addr>` frame if present, and the set of `- locked <addr>` frames. You need `tid` as the stable identity because Java thread names can repeat across pools; you must read the state from the state line because header prose is advisory only; and you must scope ownership to `- locked` frames because `- waiting on` and `- parking to wait for` describe `Object.wait` and `LockSupport.park` semantics and do not denote monitor ownership.

2. **Reduce to the `BLOCKED` sub-population and build two lookups.** Filter to stanzas whose state field equals `BLOCKED` exactly. For every `- locked <L>` address appearing in a `BLOCKED` thread's stanza, record `owner[L] = tid`; for every `BLOCKED` thread with a `- waiting to lock <L>` frame, record `waits[tid] = L`. The reason ownership is scoped to `BLOCKED` threads is subtle: the wait-for graph edge `T → U` exists only when U is itself a graph node, i.e. also `BLOCKED`. If a lock's `- locked` line lives in a `RUNNABLE` thread's stanza, the wait chain from T terminates at a non-node and cannot close a cycle — it is contention, not deadlock, no matter how many waiters pile behind it.

3. **Walk the wait-for graph and mark cycle members.** For each `BLOCKED` thread `s`, follow `owner[waits[s]]` iteratively, remembering the visited-on-this-walk set. If the walk revisits a thread already on the current path, every thread from that revisit point onward lies on a directed cycle — flag them all as deadlock members. If the walk falls off the graph (either `waits[cur]` is absent, or `owner[waits[cur]]` is absent) before revisiting, `s` is a contention-only waiter. The careless shortcut is "every `BLOCKED` thread with a `- waiting to lock` frame is deadlocked", which inflates the deadlock count by every fan-in waiter on a heavily-contended monitor whose real owner is `RUNNABLE`.

4. **Derive the four output row groups from the classification.** `DEADLOCKED_THREAD_COUNT` is the size of the deadlock set. `CONTENTION_THREAD_COUNT` is `|BLOCKED| − |deadlock|`. `DEADLOCK_LOCK` rows list every distinct address that at least one deadlock member is `- waiting to lock`. `CONTENTION_LOCK` rows list every distinct address waited on by at least one contention-only thread, minus any address already emitted as `DEADLOCK_LOCK`. The set-subtraction step matters because the same monitor can host a deadlock cycle *and* additional acyclic fan-in from unrelated `BLOCKED` threads; the row type describes the lock's canonical role, not each individual waiter's role, so a monitor that participates in any cycle stays a `DEADLOCK_LOCK`.

5. **Emit the report under `LC_ALL=C` with the fixed row order.** The two count rows come first in the mandated order, then the `DEADLOCK_LOCK` block ascending, then the `CONTENTION_LOCK` block ascending. Sort lock addresses using byte-order lex, which is what `LC_ALL=C sort` produces and what Python's `sorted()` produces on ASCII-only 16-hex strings. Write the file with a single trailing newline, no header row, no blank separator between blocks, no CSV or JSON. The pipeline shape `gawk … | python3 …` composes cleanly here: `gawk` handles the ragged multi-line stanza extraction that a stateless regex cannot, and Python handles the graph walk that `awk` can express only awkwardly.

## Fixture ground truth (private)

Thread role assignment under the opaque naming scheme:

- Deadlock cycle members (3): Worker-0003 owns 0x00007fabc47a2b1c waits 0x00007fabc4b53e91;
  Worker-0011 owns 0x00007fabc4b53e91 waits 0x00007fabc4f108a7; Worker-0005 owns 0x00007fabc4f108a7 waits 0x00007fabc47a2b1c.
- Contention lock owners (non-BLOCKED, 2): Worker-0009 RUNNABLE owns 0x00007fabc48c4d63;
  Worker-0002 TIMED_WAITING owns 0x00007fabc4d691f8.
- Contention-only BLOCKED waiters (3): Worker-0013 waits 0x00007fabc48c4d63;
  Worker-0006 waits 0x00007fabc48c4d63; Worker-0010 waits 0x00007fabc4d691f8.
- Noise threads (7): Worker-0001, Worker-0007, Worker-0015 (RUNNABLE, no
  locks); Worker-0014, Worker-0008 (WAITING park on 0x00007fabc406a2c1, 0x00007fabc4638e2a);
  Worker-0004, Worker-0012 (TIMED_WAITING waiting on 0x00007fabc42fb508, 0x00007fabc4ac7391).

Stanza order in the dump file interleaves BLOCKED (positions 3, 5, 6, 10, 11, 13)
with non-BLOCKED (positions 1, 2, 4, 7, 8, 9, 12, 14, 15) so no positional
heuristic (e.g., blocked_count_half_split by index range) reveals the split.

All monitor lock addresses in the fixture — the three deadlock monitors
(0x00007fabc47a2b1c, 0x00007fabc4b53e91, 0x00007fabc4f108a7), the two contention monitors (0x00007fabc48c4d63, 0x00007fabc4d691f8), and the
four park/wait-on noise addresses (0x00007fabc406a2c1, 0x00007fabc42fb508, 0x00007fabc4638e2a, 0x00007fabc4ac7391) — share the
prefix 0x00007fabc4, so partition-by-prefix on lock addresses reveals
nothing about the deadlock/contention split.

## Reference row set

Seven rows, canonical order:

    DEADLOCKED_THREAD_COUNT<TAB>3
    CONTENTION_THREAD_COUNT<TAB>3
    DEADLOCK_LOCK<TAB>0x00007fabc47a2b1c
    DEADLOCK_LOCK<TAB>0x00007fabc4b53e91
    DEADLOCK_LOCK<TAB>0x00007fabc4f108a7
    CONTENTION_LOCK<TAB>0x00007fabc48c4d63
    CONTENTION_LOCK<TAB>0x00007fabc4d691f8

## Traps that catch agents that are not thinking carefully

- **Trap: reading state from the stanza header prose instead of the `java.lang.Thread.State:` line.** The header `nid=0x… waiting for monitor entry [0x…]` reads like a definitive declaration, so it is tempting to `grep 'waiting for monitor entry'` and treat every match as `BLOCKED`. This silently loses `BLOCKED` threads whose header prose reads differently (transitional wording) and falsely admits threads whose `java.lang.Thread.State:` line actually says `RUNNABLE` or `TIMED_WAITING`. Every jstack stanza carries exactly one authoritative state field — the line beginning with `   java.lang.Thread.State:` — and every other cue is advisory.

- **Trap: treating `- waiting on <0xHEX16>` or `- parking to wait for <0xHEX16>` as monitor-entry blocking.** These frames look syntactically similar to `- waiting to lock <0xHEX16>` and are trivially matched by a broad pattern like `waiting.*<0x`. But `- waiting on` is emitted by `Object.wait()` (the thread has already released the monitor and is parked in its wait set), and `- parking to wait for` is emitted by `LockSupport.park` on an `AbstractQueuedSynchronizer` (which is not a monitor at all — think `ReentrantLock`, `Semaphore`, `CountDownLatch`). Neither participates in the monitor wait-for graph. A solver that lumps them in invents phantom edges and over-reports the deadlock count.

- **Trap: partitioning threads by name prefix or lock addresses by prefix.** The fixture uses opaque `Worker-XXXX` names with no semantic hint, and all lock addresses share the `0x00007fabc4` prefix with deadlock and contention monitors interleaved. Any prefix-partition heuristic misclassifies every row.

- **Trap: hardcoding the reference report or importing the runtime grader for a recital.** D5 forbids the canary tokens, the private grounding key literals, the `HARDCODED_REPORT_RECITAL_BEGIN/END` sentinels, and — as of this trap-redesign — direct references to `/tests/grader.py`, the `EXPECTED_LINES` grader constant, `from grader import` statements, and any `sys.path.insert`/`append` that reaches into `/tests`. A solver that recites the expected row set from any of these sources trips D5.

- **Trap: assuming a `Found N Java-level deadlock(s):` epilogue is present.** `jstack` *does* write a summary block naming exactly the threads and monitors involved when the JVM's built-in deadlock detector fires. But that detector runs only for `synchronized`-block monitor cycles, and this dump was captured without it — the instruction states no epilogue. Reaching for `grep -A 50 'Found.*Java-level deadlock'` yields zero matches and the solver silently emits `DEADLOCKED_THREAD_COUNT\t0`, failing every count and lock row.

- **Trap: treating `- waiting to lock` as ownership.** The verb `lock` appears in at least three distinct frame shapes: `- locked`, `- waiting to lock`, and (rarely) `- eliminated`. Only `- locked` denotes ownership. A solver that greps `\block\b` and treats every hit as ownership inverts the wait-for graph: waiters become owners, every walk terminates immediately at a self-loop or at a phantom successor, and nothing that is actually a cycle ever gets flagged.

- **Trap: emitting `DEADLOCK_LOCK` rows for the monitors that cycle members *hold*.** The `DEADLOCK_LOCK` row type describes locks that deadlock members are **waiting on**, not locks they **own**. A cycle member always holds one monitor (the one another cycle member is waiting on) and is itself waiting on a different monitor (held by yet another cycle member). Emit the waited-on addresses only; the owned addresses are named implicitly by the reverse direction of the same edges, and emitting them separately doubles the deadlock-lock set and breaks byte-identical set equality.

- **Trap: sorting lock addresses under the inherited system locale instead of `LC_ALL=C`.** Under `LC_ALL=en_US.UTF-8`, `sort` applies Unicode collation, folds case, and can reorder addresses that differ only in the case of hex digits. All addresses here are lowercase 16-hex, so the practical damage is small, but the row-ordering check demands strict ascending byte-order lex within each block, which only `LC_ALL=C sort` (or Python `sorted()` on the ASCII strings) guarantees consistently.

- **Trap: adding a header row, a blank separator line, or CRLF line endings.** The output shape demands a single trailing `\n`, two tab-separated non-empty fields per row, and no rows outside the closed row-type set `{DEADLOCKED_THREAD_COUNT, CONTENTION_THREAD_COUNT, DEADLOCK_LOCK, CONTENTION_LOCK}`. A `# jstack report v1` header, a blank line between the count block and the lock block, or `\r\n` line endings (from `echo -e` on some shells) breaks byte-identical set equality even when the classification is otherwise perfect.
