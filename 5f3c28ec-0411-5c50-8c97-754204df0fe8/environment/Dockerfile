FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        bash coreutils curl jq openssl \
        procps iproute2 diffutils util-linux \
        python3 python3-psycopg2 python3-cryptography \
        python3-fastapi python3-uvicorn python3-pydantic python3-jwt \
        python3-requests python3-yaml \
        nginx supervisor \
        gawk sed grep patch \
        gnupg2 apt-transport-https adduser \
    && install -d /etc/apt/keyrings \
    && curl -sfSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /etc/apt/keyrings/pgdg.gpg \
    && chmod 644 /etc/apt/keyrings/pgdg.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/pgdg.gpg] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-16 postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/usr/lib/postgresql/16/bin:/usr/sbin:/usr/bin:/usr/local/bin:/bin

RUN pg_dropcluster --stop 16 main 2>/dev/null || true \
    && rm -rf /var/lib/postgresql/16/main /etc/postgresql/16/main \
    && mkdir -p /var/lib/postgresql/16 /etc/postgresql/16 \
    && chown -R postgres:postgres /var/lib/postgresql /etc/postgresql

RUN (getent passwd appgate >/dev/null || adduser --system --no-create-home --group --home /nonexistent appgate) \
    && mkdir -p /var/log/postgresql \
                /var/log/nginx \
                /var/log/approval_gate \
                /var/log/supervisor \
                /var/lib/postgresql/16 \
                /var/run/postgresql \
                /workspace \
                /workspace/inbox \
                /workspace/input/baseline_manifest \
                /workspace/input/reference \
                /opt/app \
                /opt/approval_gate \
                /opt/holdout \
                /etc/app \
                /etc/approval_gate \
                /etc/approval_gate/keys \
                /etc/nginx/keys \
                /etc/nginx/conf.d \
                /etc/supervisor/conf.d \
    && chown -R appgate:appgate /etc/approval_gate /var/log/approval_gate

COPY nginx.conf.baseline                    /etc/nginx/nginx.conf
COPY approval-gate.conf.baseline            /etc/nginx/conf.d/approval-gate.conf
COPY approval_gate_config.py.baseline       /etc/approval_gate/config.py
COPY approval_gate_app.py                   /opt/approval_gate/app.py
COPY mint_token.py                          /opt/app/mint_token.py
COPY restore_cli.py                         /opt/app/restore_cli.py
COPY supervisord_services.conf              /etc/supervisor/supervisord.conf
COPY entrypoint.sh                          /usr/local/bin/entrypoint.sh
COPY README_FOR_AGENT.md                    /workspace/README_FOR_AGENT.md
COPY pinned_toolchain_manifest.yaml         /workspace/pinned_toolchain_manifest.yaml
COPY seeded_generator.py                    /opt/holdout/seeded_generator.py
COPY keyring_bootstrap.py                   /opt/holdout/keyring_bootstrap.py
COPY corruption_bootstrap.sh                /opt/holdout/corruption_bootstrap.sh
COPY inbox_msg_001.msg                      /opt/holdout/inbox_msg_001.msg
COPY inbox_msg_002.msg                      /opt/holdout/inbox_msg_002.msg
COPY inbox_msg_003.msg                      /opt/holdout/inbox_msg_003.msg

RUN chmod 755 /usr/local/bin/entrypoint.sh \
              /opt/holdout/corruption_bootstrap.sh \
              /opt/holdout/seeded_generator.py \
              /opt/holdout/keyring_bootstrap.py \
              /opt/app/mint_token.py \
              /opt/app/restore_cli.py \
              /opt/approval_gate/app.py \
    && chmod 644 /etc/nginx/nginx.conf \
                 /etc/nginx/conf.d/approval-gate.conf \
                 /etc/approval_gate/config.py \
                 /etc/supervisor/supervisord.conf \
                 /workspace/README_FOR_AGENT.md \
                 /workspace/pinned_toolchain_manifest.yaml \
    && chown appgate:appgate /etc/approval_gate/config.py /opt/approval_gate/app.py

RUN chmod 700 /opt/holdout && chown root:root /opt/holdout

WORKDIR /workspace

CMD ["/usr/local/bin/entrypoint.sh"]
