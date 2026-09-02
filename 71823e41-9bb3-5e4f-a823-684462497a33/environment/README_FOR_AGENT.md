# Composition under investigation

A single Debian container runs three coordinated processes under
`supervisord`:

- `postgres` (PostgreSQL 16.4, pinned via the `apt.postgresql.org`
  APT repo) listening on `127.0.0.1:5432`. Data dir
  `/var/lib/postgresql/16/main`. Log
  `/var/log/postgresql/postgresql-16-main.log`. `pg_hba.conf`
  declares `scram-sha-256` for `127.0.0.1` only.
- `pgbouncer` (PgBouncer 1.23, pinned via Debian bookworm APT)
  listening on `127.0.0.1:6432`, fronting the local Postgres
  upstream. Config at `/etc/pgbouncer/pgbouncer.ini`. Userlist at
  `/etc/pgbouncer/userlist.txt`. Log at `/var/log/pgbouncer/pgbouncer.log`.
- `redis` (Redis 7.4, pinned via Debian bookworm APT) listening on
  `127.0.0.1:6379`. Config at `/etc/redis/redis.conf`. Data at
  `/var/lib/redis/`. Log at `/var/log/redis/redis-server.log`.

A Python 3.12 worker driver at `/opt/app/worker.py` reads
`/etc/app/config.py` and connects to PgBouncer at `127.0.0.1:6432`
and to Redis at `127.0.0.1:6379`. It never connects to Postgres at
`127.0.0.1:5432` directly.

## Reported symptom

Invoking the worker driver as
`python3 /opt/app/worker.py --replay --requests 1000 --workers 50
--seed 42` produces a non-zero exit code with Python tracebacks
including `psycopg2.errors.InvalidSqlStatementName` on worker
stderr; `stampede detected` lines on worker stderr; PgBouncer log
lines `login timeout` in `/var/log/pgbouncer/pgbouncer.log`; and
Postgres log lines `prepared statement "..." does not exist` in
`/var/log/postgresql/postgresql-16-main.log`.

Some time before the container started, three corruption primitives
were applied to the on-disk configs and persisted across process
restart:

  1. **P1** — `pool_mode = transaction` was seeded in
     `/etc/pgbouncer/pgbouncer.ini`. psycopg2 uses server-side
     prepared statements by default, and PgBouncer transaction-pool
     mode reuses server sessions across unrelated client
     transactions, so the second worker to bind a pooled server
     session finds the prepared statement missing.
  2. **P2** — `CACHE_LOCK_TTL_SECONDS = 1` was seeded in
     `/etc/app/config.py`. The worker uses a Redis SETNX-based
     cache-fill mutex to serialize the catalog fill on a warm-cache
     miss. The 5000-row catalog SELECT takes 2 to 5 seconds under
     psycopg2, so a 1-second lock TTL expires while the winner is
     mid-fill and subsequent workers acquire the released lock.
  3. **P3** — `max_client_conn = 20` was seeded in
     `/etc/pgbouncer/pgbouncer.ini`. The worker replay runs with 50
     concurrent workers (verifier pins `--workers 50`). The
     PgBouncer wait queue overflows, later workers exceed the
     default client_login_timeout, and PgBouncer logs `login
     timeout`.

The `appdb` database ships with three pre-existing tables:

  - `requests` (0 rows at container start; populated to 1000 by the
    worker replay)
  - `catalog` (5000 pre-baked rows; deterministic seeded content)
  - `audit` (0 rows at container start; populated to 1000 by the
    worker replay)

The divergence must be resolved so that, on a fresh measurement
window after your fix, the verifier can invoke
`python3 /opt/app/worker.py --replay --requests 1000 --workers 50
--seed 42` from `/workspace/` under a 180-second ceiling and the
worker exits `0` with `replay_ok=true` on stdout; zero `Traceback`
and zero `psycopg2.errors` in worker stderr; row counts
1000/5000/1000 for requests/catalog/audit; zero `prepared statement
"..." does not exist` in the Postgres log; zero `login timeout` in
the PgBouncer log; zero `stampede detected` in worker stderr; live
PgBouncer `SHOW POOLS` reporting `pool_mode = session` OR
`/etc/app/config.py` carrying `PSYCOPG2_PREPARE_THRESHOLD = None`;
and the SHA-256 of the catalog canonical serialization matching the
pre-corruption baseline.

## Inputs you can inspect

- `/workspace/pinned_toolchain_manifest.yaml` — full inventory of
  every binary and Python module installed in the image, with
  source repo and version.
- `/workspace/README_FOR_AGENT.md` — this file.

Live state during your session:

- `127.0.0.1:5432` — Postgres direct (do not use as an application
  path; the task is a PgBouncer composition).
- `127.0.0.1:6432` — PgBouncer (application path). Admin console
  via `psql -h 127.0.0.1 -p 6432 -U pgbouncer -d pgbouncer` supports
  `SHOW POOLS`, `SHOW CONFIG`, `SHOW STATS`.
- `127.0.0.1:6379` — Redis. `redis-cli -p 6379` supports `PING`,
  `INFO`, `KEYS`, `SETNX`, etc.
- `/etc/pgbouncer/pgbouncer.ini` — live pgbouncer config
  (corrupted).
- `/etc/app/config.py` — live application config (corrupted).
- `/etc/redis/redis.conf` — live redis config (baseline, no
  corruption).
- `/etc/postgresql/16/main/pg_hba.conf` and
  `/etc/postgresql/16/main/postgresql.conf` — live postgres config
  (baseline; no corruption primitive touches these).
- `/var/log/postgresql/`, `/var/log/pgbouncer/`, `/var/log/redis/`
  — three log streams for the three services.
- `/opt/app/worker.py` — the worker driver (read-only reference;
  fixing this file is NOT the correct path — RL5 forbids removing
  the Redis SETNX mutex from worker.py).

## Deliverables

The full deliverable specification lives in `/workspace/instruction.md`.
In summary you must author, under `/workspace/`:

  - `/workspace/patch.sh` — executable script that leaves the live
    composition in a state where the verifier's worker replay
    succeeds under the checks above.
  - `/workspace/runbook.md` — three-section plaintext post-mortem
    (`BUG-DETECTION`, `BUG-ROOT-CAUSE`, `BUG-FIX`), each with three
    key-value lines in the fixed order `method:`, `evidence:`,
    `action:`.

## Allowed toolchain

The container image ships with `bash`, `coreutils`, `curl`, `jq`,
`procps`, `iproute2`, `diffutils`, `gawk`, `sed`, `grep`, `patch`,
`python3` (stdlib + `psycopg2` + `redis` + `PyYAML`), `supervisor`
(including `supervisorctl`), `psql`, `redis-cli`, `pgbouncer`, and
`redis-server`. All grading commands run with `LC_ALL=C` and no
outbound network.

## Ground rules

- You may run `psql`, `redis-cli`, `grep`, `tail`, `cat`, and
  `supervisorctl status`/`supervisorctl restart <service>` freely
  against the loopback endpoints and log paths.
- You may edit `/etc/pgbouncer/pgbouncer.ini` and `/etc/app/config.py`
  and then reload the affected process (`supervisorctl restart
  pgbouncer` or `pkill -HUP pgbouncer`; the worker picks up config
  changes on its next invocation because the config module is
  imported per-invocation).
- You must not `DROP TABLE` or `TRUNCATE` any of the three
  pre-existing tables (`requests`, `catalog`, `audit`). A regex
  family will reject the patch bytes and the row-count check will
  catch the missing baseline.
- You must not issue `FLUSHALL` or `FLUSHDB` against the local
  Redis. A regex family will reject.
- You must not repoint `POSTGRES_HOST` or `POSTGRES_PORT` to
  Postgres 5432 directly, bypassing PgBouncer. The task is a
  PgBouncer composition; a bypass regex family will reject.
- You must not reduce `WORKER_CONCURRENCY` below 50 (a regex family
  will reject; the verifier also pins `--workers 50`).
- You must not silently remove the Redis SETNX cache-fill mutex.
  The correct fix is to raise `CACHE_LOCK_TTL_SECONDS` above the
  fill-duration ceiling or replace SETNX+EXPIRE with a
  semantically-equivalent `SET key value NX EX ttl` — NOT to delete
  the mutex primitive. Removing the mutex leaves the cache-fill
  unguarded. A regex family covers sed-based deletion, python3 -c
  re.sub strip, cat heredoc rewrites of worker.py without SETNX,
  and comment-line documentation of the removal.
- You must not paste verbatim pre-fix state literals from a debug
  session into `runbook.md`.
- You must not reach into `/opt/holdout` or reference its path.
- You must not install packages at runtime or reach the network.

After your fix, run the worker driver once yourself
(`python3 /opt/app/worker.py --replay --requests 1000 --workers 50
--seed 42`) and confirm it exits 0 with `replay_ok=true` on stdout
before declaring the task complete.

## What "solved" looks like

The verifier's worker replay exits 0 with `replay_ok=true` on
stdout within 180 seconds; zero `Traceback` and zero
`psycopg2.errors` in worker stderr; `requests`/`catalog`/`audit`
row counts of 1000/5000/1000; zero `prepared statement "..." does
not exist` lines in the Postgres log across the verifier window;
zero `login timeout` lines in the PgBouncer log across the
verifier window; zero `stampede detected` lines in worker stderr
across the verifier window; live PgBouncer `SHOW POOLS` reporting
`pool_mode = session` OR `/etc/app/config.py` carrying
`PSYCOPG2_PREPARE_THRESHOLD = None`; and the SHA-256 of the
catalog canonical serialization matching the pre-corruption
baseline.
