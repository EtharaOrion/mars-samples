FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    TZ=UTC

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        coreutils \
        gawk \
        sed \
        grep \
        python3 \
        diffutils \
        patch \
        jq \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY workspace/ /workspace/

RUN mkdir -p /workspace/out && \
    chmod -R a+rX /workspace/input && \
    chmod -R a-w /workspace/input && \
    chmod -R a+rwX /workspace/out

CMD ["/bin/bash"]
