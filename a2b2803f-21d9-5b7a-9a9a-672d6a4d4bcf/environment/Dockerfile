FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        gawk \
        grep \
        jq \
        python3 \
        sed \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY workspace /workspace

# Snapshot two representative naive-attempt symptoms the agent inspects at
# task start. Both fail the D3 check against the adversarial input in a way
# a conforming csv.reader immediately surfaces.
RUN ( echo "=== naive attempt A: hand-rolled text interpolation with join(';') ===" >  /workspace/observed_naive_attempt.txt \
   && (jq -r '.[] | "\(.id),\(.name),\(.tags | join(";"))"' /workspace/tags.json 2>&1 | head -c 8192) >> /workspace/observed_naive_attempt.txt \
   && printf '\n\n' >> /workspace/observed_naive_attempt.txt \
   && echo "=== naive attempt B: @csv over exploded tags array (row per tag) ===" >> /workspace/observed_naive_attempt.txt \
   && (jq -r '.[] | [.id, .name, .tags[]] | @csv' /workspace/tags.json 2>&1 | head -c 8192) >> /workspace/observed_naive_attempt.txt \
   || true )

CMD ["/bin/bash"]
