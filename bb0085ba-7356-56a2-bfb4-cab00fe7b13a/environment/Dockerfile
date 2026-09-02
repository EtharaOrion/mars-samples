FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive

# Core toolset the agent may rely on. python3-ruamel.yaml enables the
# alternative reserialize workaround route (ruamel.yaml preserves both
# mapping anchors and sequence-element anchors on round-trip). gawk and
# sed enable the reference route (yq + post-yq re-injection of the
# dropped sequence-element anchor).
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        gawk \
        grep \
        python3 \
        python3-ruamel.yaml \
        sed \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Pin the mikefarah/yq (Go) binary at /usr/local/bin/yq which precedes
# /usr/bin on the default PATH. The known defect this task targets --
# silent drop of sequence-element anchor labels on write -- is stable
# across the v4.x line and is present at v4.53.3.
ARG TARGETARCH
RUN case "${TARGETARCH}" in \
      amd64) EXPECTED_SHA256=fa52a4e758c63d38299163fbdd1edfb4c4963247918bf9c1c5d31d84789eded4 ;; \
      arm64) EXPECTED_SHA256=578648e463a11c1b6db6010cbf41eafed6bee79466fcffa1bb446672cf7945ea ;; \
      *) echo "unsupported TARGETARCH ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    wget -q -O /usr/local/bin/yq \
        "https://github.com/mikefarah/yq/releases/download/v4.53.3/yq_linux_${TARGETARCH}" && \
    echo "${EXPECTED_SHA256}  /usr/local/bin/yq" | sha256sum -c - && \
    chmod 0755 /usr/local/bin/yq && \
    /usr/local/bin/yq --version

WORKDIR /workspace
COPY workspace /workspace

# Snapshot the naive-attempt symptom the agent inspects at task start.
# The single-yq-eval expression applies both scalar updates and deletes
# the metadata keys but leaves the sequence-element anchor `&<seq>`
# missing from the output because mikefarah yq drops it. The mapping
# anchor `&<map>` survives the same pass. Both defects are visible in
# the snapshot below.
RUN ( echo "=== naive: /usr/local/bin/yq eval single-pass update on input.yaml ===" > /workspace/observed_naive_attempt.txt \
   && /usr/local/bin/yq eval '.defaults.host = "cache-primary.svc.mars.local" | .roles[0].scope = "tenant-primary" | del(.__forge_target_mapping_path) | del(.__forge_target_mapping_value) | del(.__forge_target_sequence_path) | del(.__forge_target_sequence_value)' /workspace/input.yaml >> /workspace/observed_naive_attempt.txt 2>&1 || true ) || true

CMD ["/bin/bash"]
