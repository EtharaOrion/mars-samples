FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        bash coreutils curl jq \
        procps iproute2 diffutils util-linux \
        python3 python3-psycopg2 python3-redis python3-yaml \
        redis-server redis-tools \
        supervisor \
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

RUN (getent passwd rotator >/dev/null || adduser --system --no-create-home --group --home /nonexistent rotator) \
    && mkdir -p /var/log/postgresql \
                /var/log/redis \
                /var/log/rotator \
                /var/log/driver \
                /var/log/supervisor \
                /var/lib/postgresql/16 \
                /var/lib/redis \
                /var/run/postgresql \
                /workspace \
                /workspace/input/baseline_manifest \
                /workspace/input/reference \
                /opt/app \
                /opt/rotator \
                /opt/holdout \
                /etc/app \
                /etc/rotator \
                /etc/supervisor/conf.d \
    && chown -R rotator:rotator /var/log/rotator /etc/rotator /opt/rotator \
    && chown -R redis:redis /var/log/redis /var/lib/redis

COPY redis.conf.baseline                     /etc/redis/redis.conf
COPY rotator.conf.baseline                   /etc/rotator/rotator.conf
COPY rotator.py                              /opt/rotator/rotator.py
COPY config.py.baseline                      /etc/app/config.py
COPY apply_updates.py                        /opt/app/apply_updates.py
COPY supervisord_services.conf               /etc/supervisor/supervisord.conf
COPY entrypoint.sh                           /usr/local/bin/entrypoint.sh
COPY README_FOR_AGENT.md                     /workspace/README_FOR_AGENT.md
COPY pinned_toolchain_manifest.yaml          /workspace/pinned_toolchain_manifest.yaml
COPY seeded_generator.py                     /opt/holdout/seeded_generator.py
COPY corruption_bootstrap.sh                 /opt/holdout/corruption_bootstrap.sh

RUN chmod 755 /usr/local/bin/entrypoint.sh \
              /opt/holdout/corruption_bootstrap.sh \
              /opt/holdout/seeded_generator.py \
              /opt/rotator/rotator.py \
              /opt/app/apply_updates.py \
    && chmod 644 /etc/redis/redis.conf \
                 /etc/app/config.py \
                 /opt/app/apply_updates.py \
                 /etc/supervisor/supervisord.conf \
                 /workspace/README_FOR_AGENT.md \
                 /workspace/pinned_toolchain_manifest.yaml \
    && chmod 600 /etc/rotator/rotator.conf \
    && chown rotator:rotator /etc/rotator/rotator.conf /opt/rotator/rotator.py \
    && chown redis:redis /etc/redis/redis.conf

RUN chmod 700 /opt/holdout && chown root:root /opt/holdout

WORKDIR /workspace

CMD ["/usr/local/bin/entrypoint.sh"]
