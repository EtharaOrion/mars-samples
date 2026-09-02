# Redis single-service silent config drift

You have a single-container Redis 7 service already running as a single
service.  A background maintenance daemon silently drifts three orthogonal
axes of the live in-memory config without persisting to disk.  Bring the
live Redis state back to the baseline and document what you saw.

## Deliverables

Under `/workspace/`, author two files (and nothing else that grading
depends on):

  - `/workspace/reconcile.sh`  -- executable; when invoked as
    `bash /workspace/reconcile.sh` from `/workspace/` with `LC_ALL=C` and
    the pinned toolchain on `PATH`, it MUST drive the live Redis state back
    to the baseline (`appendonly=yes`, `aof_enabled=1`,
    `maxmemory-policy=allkeys-lru`, TLS handshake against the current CA
    succeeds, `PING` returns `PONG`), exit `0`, and leave the server
    responsive to subsequent commands over both the unix socket and the
    TLS port.

  - `/workspace/runbook.md`  -- plaintext; exactly three sections in the
    pinned order `DRIFT-PERSISTENCE`, `DRIFT-EVICTION`, `DRIFT-TLS`, each
    opened by the literal heading line `### DRIFT-<ID>` and each carrying
    three key-value lines in the fixed order `detected_by:`, `evidence:`,
    `reconciliation:` whose values reflect the POST-DRIFT observations you
    actually made -- not the pre-drift baseline readout.

## What is baseline

  - `appendonly yes` (AOF persistence enabled; `aof_enabled:1`)
  - `maxmemory-policy allkeys-lru`
  - TLS enforced on port 6380 via the cert pair at `/etc/redis/tls/`
  - Unix socket at `/var/run/redis/redis.sock`

The exact bytes of the baseline `redis.conf` are readable at
`/workspace/input/baseline_config/redis.conf.baseline`.  The baseline TLS
trust anchor bytes are readable at
`/workspace/input/tls_snapshot/ca.crt.baseline`.

## What drifts silently

A background loop cycles three drift states with a cadence of tens of
seconds:
  - a persistence flip via `CONFIG SET` (in-memory only; not persisted);
  - an eviction-policy flip via `CONFIG SET` (in-memory only);
  - a TLS trust-anchor rotation via `mv` of `.new` bytes over the anchor.

The loop also touches `/var/lib/redis/mutation_tick` on every cycle so the
verifier can prove the loop was live during the run window.  It is not a
cron job and not a systemd timer.

Read `/workspace/README_FOR_AGENT.md` for the full file inventory, the
allowed toolchain, the red-line list, and the grading surface.
