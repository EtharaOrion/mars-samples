FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        gawk \
        grep \
        python3 \
        ripgrep \
        sed \
    && rm -rf /var/lib/apt/lists/*

# Agent-visible workspace seed. Delivers /workspace/source.c and
# /workspace/source_holdout.c (the two seeded source files whose bytes
# are frozen at task start and whose SHA-256 the grader verifies) plus
# /workspace/expected.txt (the public expected extraction, delivered as
# an agent-visible target shape). All three files are derived from
# solution/grounding.yaml by solution/recompute.py at bundle authoring
# time and copied unchanged into the image.
WORKDIR /workspace
COPY workspace /workspace

WORKDIR /workspace
CMD ["/bin/bash"]
