# Service under investigation

A single Debian container runs two processes under `supervisord`:

- `prometheus` (server, HTTP on `127.0.0.1:9090`) scrapes the app every 5s
  using `/etc/prometheus/prometheus.yml`.
- `app` (`python3 /app/main.py`, HTTP on `127.0.0.1:8080`) exports
  `http_requests_total{route,status}` via `/metrics` and self-generates
  synthetic traffic against a fixed set of routes and statuses.

Every request the app records is also appended as a JSONL line to
`/var/log/app/audit.log` with fields `ts` (epoch milliseconds),
`route`, and `status`.

## Reported symptom

Operations reports that `http_requests_total` diverges from the audit
log after the container has been running for a while: the counter
value queried through PromQL no longer matches the number of audit-log
events for the same `(route, status)` tuple.

The divergence must be resolved so that, on a fresh measurement window
after your fix, the difference between the audit-log count and the
PromQL instant value for every canonical `(route, status)` pair is
bounded by an absolute tolerance of 40 samples.

## Inputs you can inspect

- `/workspace/input/baseline_app/` - read-only baseline copies of the
  app source (`main.py.baseline`) and the Prometheus config
  (`prometheus.yml.baseline`) as shipped in the image.
- `/workspace/input/promql_readout/promql_readout.txt.baseline` -
  read-only reference showing the canonical set of series shapes that
  are supposed to be present, one per line, with `<N>` placeholders in
  place of counter values (which vary per run).
- `/workspace/input/audit_log_snapshot/audit.log.baseline` - read-only
  snapshot of the audit log at image build time (may be empty).

Live state during your session:

- `/app/main.py` - the running app source.
- `/etc/prometheus/prometheus.yml` - the live Prometheus config.
- `/var/log/app/audit.log` - the live audit log, appended to on every
  request.
- `http://127.0.0.1:9090` - Prometheus HTTP endpoint (query API only;
  no admin API).
- `http://127.0.0.1:8080/metrics` - app metrics endpoint.

## Deliverables

The full deliverable specification lives in
`/workspace/instruction.md`.  In summary you must author, under
`/workspace/`:

  - `/workspace/patch.sh`  --  executable script that drives the live
    system back to canonical behaviour.
  - `/workspace/runbook.md`  --  three-section plaintext post-mortem
    (`SYMPTOM`, `ROOT-CAUSE`, `FIX`).

## Allowed toolchain

The container image ships with `bash`, `coreutils`, `curl`, `jq`,
`procps`, `iproute2`, `diffutils`, `gawk`, `sed`, `grep`, `patch`,
`python3` (with `prometheus_client` and `PyYAML`), `supervisor`
(including `supervisorctl`), and `prometheus`.  All grading commands
run with `LC_ALL=C` and no network.

## Ground rules

- You may modify `/app/main.py` and `/etc/prometheus/prometheus.yml`.
- You may restart individual programs with
  `supervisorctl restart app` or `supervisorctl restart prometheus`.
  Do not kill `supervisord` itself.
- You must not tamper with `/var/log/app/audit.log` (it is the source
  of truth against which the counters are compared).  Any patch that
  rewrites, truncates, `sed -i`-mutates, or otherwise touches the
  audit-log bytes will be rejected by static regex before it even
  runs.
- You must not add scrape-time relabel rules, recording rules,
  federation, `remote_write`, `remote_read`, honor_labels shortcuts,
  or any other Prometheus feature that invents series values.
- You must not enable the Prometheus admin API or POST to
  `/api/v1/admin/tsdb/*`.  Admin API is off at process start; the
  regex family will still reject the patch bytes.
- You must not paste the pre-mutation readout content verbatim into
  your deliverables.
- You must not reach into `/opt/holdout` or reference its path.
- You must not install packages at runtime or reach the network.

After your fix, allow at least 20 seconds and three consecutive
scrapes to pass before declaring the task complete, so the counters
can restabilise.

## What "solved" looks like

For each canonical `(route, status)` in the reference readout, the
absolute difference between the audit-log count and the PromQL
instant value of `http_requests_total{route=...,status=...}` over a
fresh measurement window must be at most 40 samples.  Both
`supervisorctl status app prometheus` entries must report `RUNNING`,
`curl -sf http://127.0.0.1:9090/-/ready` must return HTTP 200, and
`curl -sf http://127.0.0.1:8080/metrics` must return HTTP 200.
