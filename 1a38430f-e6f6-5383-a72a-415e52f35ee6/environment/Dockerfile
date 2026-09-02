FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C
ENV LANG=C.UTF-8

RUN echo "deb http://deb.debian.org/debian bookworm-backports main" \
        > /etc/apt/sources.list.d/backports.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        bash coreutils \
        openssl \
        procps iproute2 diffutils \
        python3 jq \
        gawk sed grep patch \
    && apt-get install -y --no-install-recommends -t bookworm-backports \
        redis-server redis-tools \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/usr/bin:/usr/local/bin:/bin
ENV REDIS_SOCK=/var/run/redis/redis.sock

RUN mkdir -p /etc/redis /etc/redis/tls \
             /var/lib/redis /var/lib/redis/appendonlydir \
             /var/run/redis /var/log/redis \
             /workspace \
             /workspace/input/baseline_config \
             /workspace/input/tls_snapshot \
             /workspace/input/reference \
             /opt/holdout

COPY redis.conf.baseline      /etc/redis/redis.conf
COPY redis.conf.baseline      /workspace/input/baseline_config/redis.conf.baseline
COPY seed_workload.py         /tmp/seed_workload.py
COPY seed_cluster.sh          /tmp/seed_cluster.sh
COPY drift_tick               /usr/local/bin/drift_tick
COPY entrypoint.sh            /usr/local/bin/entrypoint.sh
COPY README_FOR_AGENT.md      /workspace/README_FOR_AGENT.md

RUN chmod 755 /tmp/seed_cluster.sh /usr/local/bin/drift_tick /usr/local/bin/entrypoint.sh \
    && chmod 644 /etc/redis/redis.conf /workspace/input/baseline_config/redis.conf.baseline \
    && chmod 644 /workspace/README_FOR_AGENT.md

RUN /tmp/seed_cluster.sh

RUN chmod -R a-w /workspace/input/baseline_config \
                 /workspace/input/tls_snapshot \
                 /workspace/input/reference \
    && chmod 700 /opt/holdout \
    && find /opt/holdout -type f -exec chmod 400 {} \;

WORKDIR /workspace

CMD ["/usr/local/bin/entrypoint.sh"]
