FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1

RUN echo "deb http://deb.debian.org/debian bookworm-backports main" \
        > /etc/apt/sources.list.d/backports.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        bash coreutils curl jq \
        procps iproute2 diffutils \
        python3 python3-prometheus-client python3-yaml \
        supervisor \
        gawk sed grep patch \
    && apt-get install -y --no-install-recommends -t bookworm-backports \
        prometheus \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/usr/bin:/usr/local/bin:/bin

RUN mkdir -p /etc/prometheus \
             /var/lib/prometheus \
             /var/log/app \
             /var/log/supervisor \
             /app \
             /workspace \
             /workspace/input/baseline_app \
             /workspace/input/promql_readout \
             /workspace/input/audit_log_snapshot \
             /opt/holdout \
             /etc/supervisor/conf.d

COPY prometheus.yml.baseline      /etc/prometheus/prometheus.yml
COPY prometheus.yml.baseline      /workspace/input/baseline_app/prometheus.yml.baseline
COPY app_main.py                  /app/main.py
COPY app_main.py                  /workspace/input/baseline_app/main.py.baseline
COPY reference_promql_readout.txt /workspace/input/promql_readout/promql_readout.txt.baseline
COPY audit_log_baseline           /workspace/input/audit_log_snapshot/audit.log.baseline
COPY supervisord_app.conf         /etc/supervisor/supervisord.conf
COPY entrypoint.sh                /usr/local/bin/entrypoint.sh
COPY README_FOR_AGENT.md          /workspace/README_FOR_AGENT.md

RUN chmod 755 /usr/local/bin/entrypoint.sh /app/main.py \
    && chmod 644 /etc/prometheus/prometheus.yml \
                 /workspace/input/baseline_app/prometheus.yml.baseline \
                 /workspace/input/baseline_app/main.py.baseline \
                 /workspace/input/promql_readout/promql_readout.txt.baseline \
                 /workspace/input/audit_log_snapshot/audit.log.baseline \
                 /workspace/README_FOR_AGENT.md \
                 /etc/supervisor/supervisord.conf

RUN chmod -R a-w /workspace/input/baseline_app \
                 /workspace/input/promql_readout \
                 /workspace/input/audit_log_snapshot \
    && chmod 700 /opt/holdout

WORKDIR /workspace

CMD ["/usr/local/bin/entrypoint.sh"]
