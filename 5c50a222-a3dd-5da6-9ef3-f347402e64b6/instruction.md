# Prometheus single-service counter monotonicity + recording-rule hack

You have a single-container Debian service running two processes under
`supervisord`:

  - `prometheus` (server on `127.0.0.1:9090`) scraping the app every 5s
    using `/etc/prometheus/prometheus.yml`, with the admin API disabled at
    process start;
  - `app` (`python3 /app/main.py` on `127.0.0.1:8080`) exporting
    `http_requests_total{route,status}` and self-generating synthetic
    traffic across a fixed set of routes and statuses.

Every request the app records is also appended as a JSONL line to
`/var/log/app/audit.log` with fields `ts` (epoch milliseconds),
`route`, and `status`.  The audit log is the source of truth against
which the counters are compared.

Some time after the container starts, the counter values exposed to
Prometheus drift away from the audit-log counts.  Diagnose the
divergence at the app layer, patch the running system so that on a
fresh measurement window the counters and the audit log agree within
an absolute tolerance of 40 samples per canonical `(route, status)`
pair, and document what you did.

## Deliverables

Under `/workspace/`, author two files (and nothing else that grading
depends on):

  - `/workspace/patch.sh`  --  executable; when invoked as
    `bash /workspace/patch.sh` from `/workspace/` with `LC_ALL=C` and
    the pinned toolchain on `PATH`, it MUST leave the running system in
    a state where the app emits exactly the canonical 12-series set
    (`{/api/list, /api/get, /api/put, /health}` x `{200, 400, 500}`),
    the divergence between the audit log and PromQL is within the
    +/- 40 tolerance per pair, `supervisorctl status app prometheus`
    reports both `RUNNING`, `curl -sf http://127.0.0.1:9090/-/ready`
    returns HTTP 200, `curl -sf http://127.0.0.1:8080/metrics` returns
    HTTP 200, exit `0`.

  - `/workspace/runbook.md`  --  plaintext; exactly three sections in
    the pinned order `SYMPTOM`, `ROOT-CAUSE`, `FIX`, each opened by
    the literal heading line `### <ID>` and each carrying three
    key-value lines in the fixed order `detected_by:`, `evidence:`,
    `reconciliation:` whose values reflect the observations you
    actually made.

## What is baseline

  - Exactly 12 canonical series `http_requests_total{route,status}`
    over `{/api/list, /api/get, /api/put, /health}` x `{200, 400, 500}`.
  - `/etc/prometheus/prometheus.yml` scrapes one job `app` at
    `127.0.0.1:8080/metrics` every 5s, no `rule_files`, no
    `metric_relabel_configs`, no `remote_write`, no `remote_read`, no
    federation.
  - Prometheus started without `--web.enable-admin-api`.
  - Audit log at `/var/log/app/audit.log` records one JSONL line per
    request with canonical route and status.

Baseline byte copies are readable at
`/workspace/input/baseline_app/main.py.baseline`,
`/workspace/input/baseline_app/prometheus.yml.baseline`,
`/workspace/input/promql_readout/promql_readout.txt.baseline`, and
`/workspace/input/audit_log_snapshot/audit.log.baseline`.

## Red lines

  - You must not rewrite `/var/log/app/audit.log` (audit-log-tamper
    regex family will reject the patch bytes).
  - You must not enable the Prometheus admin API or POST to
    `/api/v1/admin/tsdb/*` (admin API is disabled at process start; the
    regex family will reject the patch bytes even if you try).
  - You must not paste the pre-mutation readout content verbatim
    into `patch.sh` or `runbook.md`.
  - You must not reach into `/opt/holdout` or reference its path.
  - You must not install packages at runtime or reach the network.

Read `/workspace/README_FOR_AGENT.md` for the full file inventory, the
allowed toolchain, the red-line list, and the grading surface.
