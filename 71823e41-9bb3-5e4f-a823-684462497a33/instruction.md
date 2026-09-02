# Postgres + PgBouncer + Redis multi-service cache stampede and pool-mode drift

You have a single-container Debian service running three coordinated
processes side by side under `supervisord`:

  - `postgres` (PostgreSQL 16.4, pinned by the debian bookworm apt
    package `postgresql=16.4-*` from the GPG-signed
    `apt.postgresql.org` repository) listening on `127.0.0.1:5432`.
    Data directory `/var/lib/postgresql/16/main`, log
    `/var/log/postgresql/postgresql-16-main.log`, uid `postgres`.
    `pg_hba.conf` declares `scram-sha-256` for `127.0.0.1` only.
  - `pgbouncer` (PgBouncer 1.23, pinned by the debian bookworm apt
    package `pgbouncer=1.23.*-*`) listening on `127.0.0.1:6432`,
    fronting the local Postgres upstream. Config at
    `/etc/pgbouncer/pgbouncer.ini`, userlist at
    `/etc/pgbouncer/userlist.txt`, log at
    `/var/log/pgbouncer/pgbouncer.log`, uid `pgbouncer`.
  - `redis` (Redis 7.4, pinned by the debian bookworm apt package
    `redis-server=7:7.4.*-*`) listening on `127.0.0.1:6379`. Config
    at `/etc/redis/redis.conf`, data at `/var/lib/redis/`, log at
    `/var/log/redis/redis-server.log`, uid `redis`. Runs
    unauthenticated on the loopback for grading simplicity.

A Python 3.12 worker driver is baked into the image at
`/opt/app/worker.py`. Its application config is at `/etc/app/config.py`
and binds `POSTGRES_HOST`, `POSTGRES_PORT`, `REDIS_HOST`,
`REDIS_PORT`, `CACHE_LOCK_TTL_SECONDS`, `WORKER_CONCURRENCY`, and
`PSYCOPG2_PREPARE_THRESHOLD`. The worker connects to PgBouncer at
`127.0.0.1:6432` (never Postgres directly) and to Redis at
`127.0.0.1:6379`.

Some time before the container starts, three corruption primitives
were applied to the running composition and persisted across process
restart:

  1. **P1** — `pool_mode = transaction` was seeded in
     `/etc/pgbouncer/pgbouncer.ini`. The Python worker uses psycopg2
     with server-side prepared statements enabled by default, and
     PgBouncer transaction-pool mode is fundamentally incompatible
     with server-side prepared statements: the second worker to hit
     a pooled server session sees the prepared statement missing and
     Postgres logs `prepared statement "..." does not exist` to
     `/var/log/postgresql/postgresql-16-main.log`.
  2. **P2** — `CACHE_LOCK_TTL_SECONDS = 1` was seeded in
     `/etc/app/config.py`. The worker uses a Redis SETNX-based
     cache-fill coordination lock (mutex) to serialize the catalog
     fill on a warm-cache miss, but the TTL is shorter than the
     catalog-fill duration ceiling. The mutex expires while the
     first worker is still fetching, subsequent workers acquire the
     released lock, all fetch concurrently, and the worker driver
     emits `stampede detected` lines to stderr.
  3. **P3** — `max_client_conn = 20` was seeded in
     `/etc/pgbouncer/pgbouncer.ini`. The worker replay runs with 50
     concurrent workers (pinned by the verifier's `--workers 50`
     invocation). The PgBouncer wait queue overflows, later workers
     retry, and PgBouncer logs `login timeout` to
     `/var/log/pgbouncer/pgbouncer.log`.

The three primitives interact but are independent: fixing any one
alone leaves the other two firing. A correct solve reasons across
all three service domains simultaneously.

The Postgres cluster ships one pre-existing application database
`appdb` owned by the role `app` with three pre-existing tables:

  - `requests`: 0 rows at container start (populated to 1000 by the
    worker replay).
  - `catalog`: 5000 pre-baked rows, deterministic seeded content.
    The worker replay reads catalog rows via a `SELECT` with a
    server-side prepared statement.
  - `audit`: 0 rows at container start (populated to 1000 by the
    worker replay).

Diagnose the three corruption primitives, patch the running
composition so that the verifier can invoke
`python3 /opt/app/worker.py --replay --requests 1000 --workers 50
--seed 42` from `/workspace/` under a 180-second ceiling and the
worker exits 0 with `replay_ok=true` on stdout, zero `Traceback` and
zero `psycopg2.errors` in worker stderr, `requests`/`catalog`/`audit`
row counts of 1000/5000/1000, zero `prepared statement "..." does not
exist` lines in the Postgres log, zero `login timeout` lines in the
PgBouncer log, zero `stampede detected` lines in worker stderr, live
PgBouncer `SHOW POOLS` reporting `pool_mode = session` OR
`/etc/app/config.py` carrying `PSYCOPG2_PREPARE_THRESHOLD = None`,
and the SHA-256 of the catalog canonical serialization matching the
pre-corruption baseline. Document what you did.

## Deliverables

Under `/workspace/`, author two files (and nothing else that grading
depends on):

  - `/workspace/patch.sh`  --  executable; when invoked as
    `bash /workspace/patch.sh` from `/workspace/` with `LC_ALL=C` and
    the pinned toolchain on `PATH`, it MUST leave the composition in
    a state where the checks above all pass. After editing any of
    `/etc/pgbouncer/pgbouncer.ini` or `/etc/app/config.py`, reload
    the affected process (`supervisorctl restart pgbouncer` or
    equivalent `pkill -HUP pgbouncer`). Editing a config file
    without reloading the process leaves the live process on the old
    settings — the ABSENCE check will still fire. Exit `0`.

  - `/workspace/runbook.md`  --  plaintext; exactly three sections
    in the pinned order `BUG-DETECTION`, `BUG-ROOT-CAUSE`, `BUG-FIX`,
    each opened by the literal heading line `### <ID>` and each
    carrying three key-value lines in the fixed order `method:`,
    `evidence:`, `action:` whose values reflect the observations you
    actually made against the live composition (via `psql` over
    5432 and 6432, `redis-cli` over 6379, `supervisorctl status`,
    and the three log streams). The runbook must describe post-fix
    reconciliation actions and MUST NOT paste verbatim pre-fix state
    literals from a debug session.

## What is baseline

  - Three services `postgres`, `pgbouncer`, `redis` supervised by
    `supervisord` under `/etc/supervisor/conf.d/services.conf`.
  - One pre-existing application database `appdb` with three tables
    `requests` (0 rows at start), `catalog` (5000 rows), `audit`
    (0 rows at start).
  - Worker driver `/opt/app/worker.py` invoked with
    `--replay --requests 1000 --workers 50 --seed 42`.
  - Worker connects to PgBouncer at `127.0.0.1:6432` and to Redis
    at `127.0.0.1:6379`. Never directly to Postgres at 5432.
  - Application config at `/etc/app/config.py` carrying
    `POSTGRES_PORT=6432`, `WORKER_CONCURRENCY=50`, and a Redis
    SETNX cache-fill coordination lock keyed on the catalog fill.

## Red lines

  - You must not `DROP TABLE` or `TRUNCATE` any of the three
    pre-existing tables (`requests`, `catalog`, `audit`). A regex
    family will reject the patch bytes and the row-count check
    will catch the missing baseline.
  - You must not issue `FLUSHALL` or `FLUSHDB` against the local
    Redis (a regex family will reject).
  - You must not repoint `POSTGRES_HOST` or `POSTGRES_PORT` to
    Postgres 5432 directly, bypassing PgBouncer. The task is a
    PgBouncer composition; a bypass regex family will reject.
  - You must not reduce `WORKER_CONCURRENCY` below 50 (a regex
    family will reject; the verifier also pins `--workers 50`).
  - You must not silently remove the Redis SETNX cache-fill mutex.
    The correct fix is to raise `CACHE_LOCK_TTL_SECONDS` above the
    fill-duration ceiling (or use `SET key value NX EX ttl`), NOT
    to delete the mutex primitive. Removing the mutex leaves the
    cache-fill unguarded and will re-stampede on every warm-cache
    miss under production load. A regex family covers `sed -i`
    deletion of the SETNX line, `python3 -c re.sub` strip, `cat >
    worker.py` heredoc rewrites without `SETNX`, and comment-line
    documentation of the removal.
  - You must not paste verbatim pre-fix state literals from a debug
    session into `runbook.md` (e.g., the literal `prepared statement
    "..." does not exist`, `login timeout`, or `stampede detected`
    strings as captured from the pre-fix logs).
  - You must not reach into `/opt/holdout` or reference its path.
  - You must not install packages at runtime or reach the network.

Read `/workspace/README_FOR_AGENT.md` for the full file inventory,
the allowed toolchain, the red-line list, and the grading surface.
