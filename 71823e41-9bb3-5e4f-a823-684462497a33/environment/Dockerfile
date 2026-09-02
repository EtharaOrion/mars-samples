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
        supervisor \
        gawk sed grep patch \
        gnupg2 apt-transport-https \
        pgbouncer \
        redis-server redis-tools \
        adduser \
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

RUN mkdir -p /var/log/postgresql \
             /var/log/pgbouncer \
             /var/log/redis \
             /var/log/supervisor \
             /var/run/pgbouncer \
             /var/run/redis \
             /var/lib/redis \
             /workspace \
             /opt/app \
             /opt/holdout \
             /etc/app \
             /etc/supervisor/conf.d

COPY pgbouncer.ini.baseline        /etc/pgbouncer/pgbouncer.ini
COPY config.py.baseline            /etc/app/config.py
COPY redis.conf.baseline           /etc/redis/redis.conf
COPY supervisord_services.conf     /etc/supervisor/supervisord.conf
COPY entrypoint.sh                 /usr/local/bin/entrypoint.sh
COPY worker.py                     /opt/app/worker.py
COPY README_FOR_AGENT.md           /workspace/README_FOR_AGENT.md
COPY pinned_toolchain_manifest.yaml /workspace/pinned_toolchain_manifest.yaml
COPY seeded_generator.py           /opt/holdout/seeded_generator.py
COPY corruption_bootstrap.sh       /opt/holdout/corruption_bootstrap.sh

RUN (getent passwd pgbouncer >/dev/null || adduser --system --no-create-home --group --home /nonexistent pgbouncer) \
    && (getent passwd redis     >/dev/null || adduser --system --no-create-home --group --home /var/lib/redis redis) \
    && printf '"pgbouncer" "pgbouncer-password"\n' \
      > /etc/pgbouncer/userlist.txt \
    && printf '"app" "app-password"\n' \
      >> /etc/pgbouncer/userlist.txt \
    && chown pgbouncer:pgbouncer /etc/pgbouncer/pgbouncer.ini /etc/pgbouncer/userlist.txt \
    && chmod 640 /etc/pgbouncer/pgbouncer.ini /etc/pgbouncer/userlist.txt \
    && chown redis:redis /etc/redis/redis.conf \
    && chmod 640 /etc/redis/redis.conf \
    && chmod 755 /usr/local/bin/entrypoint.sh \
                 /opt/holdout/corruption_bootstrap.sh \
                 /opt/holdout/seeded_generator.py \
    && chmod 644 /opt/app/worker.py \
                 /etc/app/config.py \
                 /etc/supervisor/supervisord.conf \
                 /workspace/README_FOR_AGENT.md \
                 /workspace/pinned_toolchain_manifest.yaml

RUN chmod 700 /opt/holdout && chown root:root /opt/holdout

WORKDIR /workspace

CMD ["/usr/local/bin/entrypoint.sh"]
