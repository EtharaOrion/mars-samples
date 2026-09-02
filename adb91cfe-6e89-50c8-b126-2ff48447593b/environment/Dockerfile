FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        gcc \
        libc6-dev \
        make \
        python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY workspace /workspace

# Snapshot the naive-attempt symptom the agent inspects at task start.
# The probe runs `make test` twice in a scratch copy so it does not
# pollute the live /workspace tree. On the second invocation the .PHONY
# gap at the root and inside subdir/ silently skips the recipe, which is
# the symptom the agent must chase.
RUN cp -a /workspace /tmp/probe \
 && (cd /tmp/probe && make test 2>&1) > /workspace/observed_naive_attempt.txt \
 && echo "" >> /workspace/observed_naive_attempt.txt \
 && echo "=== SECOND INVOCATION OF make test (SAME TREE, NO CLEAN) ===" >> /workspace/observed_naive_attempt.txt \
 && (cd /tmp/probe && make test 2>&1) >> /workspace/observed_naive_attempt.txt \
 && echo "" >> /workspace/observed_naive_attempt.txt \
 && echo "=== SECOND INVOCATION OF make build (SAME TREE) ===" >> /workspace/observed_naive_attempt.txt \
 && (cd /tmp/probe && make build 2>&1) >> /workspace/observed_naive_attempt.txt \
 && (cd /tmp/probe && make build 2>&1) >> /workspace/observed_naive_attempt.txt \
 && rm -rf /tmp/probe \
 && chmod -R a+rw /workspace

CMD ["/bin/bash"]
