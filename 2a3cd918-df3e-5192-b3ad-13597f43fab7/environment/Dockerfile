FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        gawk \
        git \
        grep \
        python3 \
        sed \
    && rm -rf /var/lib/apt/lists/*

# Agent-visible workspace seed. Delivers /workspace/expected.txt (the public
# expected aggregate for the target author, bytes derived from
# solution/grounding.yaml by solution/recompute.py) as an agent-visible
# target shape.
WORKDIR /workspace
COPY workspace /workspace

# Seed the git repository at /workspace/repo deterministically. The setup
# script pins GIT_AUTHOR_DATE and GIT_COMMITTER_DATE per commit and disables
# gpg signing so numstat output is reproducible across build hosts. The same
# script also generates /workspace/observed_naive_attempt.txt at build time
# by running two representative naive git-log pipelines against the seeded
# repo so the agent can see the trap shapes at task start.
COPY setup_repo.sh /tmp/setup_repo.sh
RUN bash /tmp/setup_repo.sh && rm -f /tmp/setup_repo.sh

WORKDIR /workspace
CMD ["/bin/bash"]
