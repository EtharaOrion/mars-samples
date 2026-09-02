FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV ES_PATH_CONF=/etc/elasticsearch
ENV ES_JAVA_HOME=/usr/lib/jvm/java-17-openjdk-${TARGETARCH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        bash coreutils curl jq \
        procps iproute2 diffutils util-linux \
        python3 python3-yaml \
        supervisor \
        gawk sed grep patch \
        gnupg2 apt-transport-https \
        openjdk-17-jre-headless \
        adduser \
    && install -d /etc/apt/keyrings \
    && curl -sfSL https://artifacts.elastic.co/GPG-KEY-elasticsearch \
        | gpg --dearmor -o /etc/apt/keyrings/elastic.gpg \
    && chmod 644 /etc/apt/keyrings/elastic.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/elastic.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" \
        > /etc/apt/sources.list.d/elastic-8.x.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends elasticsearch=8.13.4 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/usr/share/elasticsearch/bin:/usr/bin:/usr/local/bin:/bin

RUN mkdir -p /var/log/elasticsearch \
             /var/lib/elasticsearch \
             /var/log/supervisor \
             /workspace \
             /opt/holdout \
             /etc/supervisor/conf.d \
             /etc/elasticsearch/jvm.options.d

COPY elasticsearch.yml.baseline    /etc/elasticsearch/elasticsearch.yml
COPY jvm.options.baseline          /etc/elasticsearch/jvm.options.d/00-heap.options
COPY supervisord_es.conf           /etc/supervisor/supervisord.conf
COPY entrypoint.sh                 /usr/local/bin/entrypoint.sh
COPY README_FOR_AGENT.md           /workspace/README_FOR_AGENT.md
COPY pinned_toolchain_manifest.yaml /workspace/pinned_toolchain_manifest.yaml
COPY seeded_generator.py           /opt/holdout/seeded_generator.py
COPY corruption_bootstrap.sh       /opt/holdout/corruption_bootstrap.sh

RUN chown -R elasticsearch:elasticsearch \
        /var/log/elasticsearch \
        /var/lib/elasticsearch \
        /etc/elasticsearch \
    && chmod 755 /usr/local/bin/entrypoint.sh \
                 /opt/holdout/corruption_bootstrap.sh \
                 /opt/holdout/seeded_generator.py \
    && chmod 644 /etc/elasticsearch/elasticsearch.yml \
                 /etc/elasticsearch/jvm.options.d/00-heap.options \
                 /etc/supervisor/supervisord.conf \
                 /workspace/README_FOR_AGENT.md \
                 /workspace/pinned_toolchain_manifest.yaml

RUN chmod 700 /opt/holdout \
    && chown root:root /opt/holdout

WORKDIR /workspace

CMD ["/usr/local/bin/entrypoint.sh"]
