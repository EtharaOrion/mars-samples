FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nginx-full openssl curl python3 jq iproute2 procps ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY workspace/ /workspace/
COPY build_pki.sh /tmp/build_pki.sh
COPY upstream_server.py /opt/upstream/upstream_server.py
COPY entrypoint.sh /entrypoint.sh

RUN mkdir -p /opt/upstream /var/log/nginx /var/log/upstream && \
    cp /workspace/input/upstream/index.html /opt/upstream/index.html && \
    chmod 0755 /tmp/build_pki.sh /opt/upstream/upstream_server.py /entrypoint.sh && \
    bash /tmp/build_pki.sh && \
    rm -f /tmp/build_pki.sh

EXPOSE 80 443 8080
ENTRYPOINT ["/entrypoint.sh"]
