FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates wget gnupg lsb-release \
    && wget -qO /etc/apt/trusted.gpg.d/postgresql.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        postgresql-16 \
        postgresql-client-16 \
        procps iproute2 \
        python3 jq coreutils bash sudo \
    && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/pgdg.list

ENV PATH=/usr/lib/postgresql/16/bin:$PATH
ENV PGDATA=/var/lib/postgresql/data

RUN mkdir -p /var/lib/postgresql/data /workspace \
             /workspace/input/pg_wal_snapshot \
             /workspace/input/basebackup \
             /workspace/input/reference \
             /var/run/postgresql /opt/holdout \
    && chown -R postgres:postgres /var/lib/postgresql /workspace /var/run/postgresql

COPY seed_cluster.sh          /tmp/seed_cluster.sh
COPY rotate_pg_hba            /usr/local/bin/rotate_pg_hba
COPY entrypoint.sh            /usr/local/bin/entrypoint.sh
COPY README_FOR_AGENT.md      /workspace/README_FOR_AGENT.md

RUN chmod 755 /tmp/seed_cluster.sh /usr/local/bin/rotate_pg_hba /usr/local/bin/entrypoint.sh \
    && chown postgres:postgres /workspace/README_FOR_AGENT.md

RUN mkdir -p /etc/postgresql-common \
    && printf 'postgres-inv23-hint-only-2ec9a3b7c4d1\n' > /etc/postgresql-common/pgpass_hint \
    && chmod 400 /etc/postgresql-common/pgpass_hint \
    && chown postgres:postgres /etc/postgresql-common/pgpass_hint

USER postgres
RUN /tmp/seed_cluster.sh

USER root
RUN if [ -f /var/lib/postgresql/reference_ceiling.lsn ]; then \
      mv /var/lib/postgresql/reference_ceiling.lsn /opt/holdout/reference_ceiling.lsn ; \
    fi \
    && if [ -f /var/lib/postgresql/checkpoint_lsn_at_dump.txt ]; then \
      mv /var/lib/postgresql/checkpoint_lsn_at_dump.txt /opt/holdout/checkpoint_lsn_at_dump.txt ; \
    fi \
    && chown -R root:postgres /opt/holdout \
    && chmod 750 /opt/holdout \
    && find /opt/holdout -type f -exec chmod 440 {} \;

USER postgres
WORKDIR /workspace

CMD ["/usr/local/bin/entrypoint.sh"]
