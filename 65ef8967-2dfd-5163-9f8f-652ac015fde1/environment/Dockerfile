# syntax=docker/dockerfile:1.6
FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      coreutils \
      bash \
      gawk \
      mawk \
      python3 \
 && update-alternatives --set awk /usr/bin/gawk \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /workspace /logs/verifier
COPY workspace/data.txt /workspace/data.txt
COPY workspace/expected_output.txt /workspace/expected_output.txt
COPY workspace/observed_naive_attempt.txt /workspace/observed_naive_attempt.txt

WORKDIR /workspace
CMD ["/bin/bash"]
