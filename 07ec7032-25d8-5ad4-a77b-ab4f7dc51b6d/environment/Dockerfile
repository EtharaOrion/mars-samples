FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        gawk \
        grep \
        jq \
        python3 \
        sed \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY workspace /workspace

CMD ["/bin/bash"]
