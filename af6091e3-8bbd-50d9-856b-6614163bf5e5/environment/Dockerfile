FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      podman uidmap fuse-overlayfs slirp4netns passt ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 -s /bin/bash appuser
COPY alpine.tar /opt/alpine.tar
RUN chmod 0644 /opt/alpine.tar
RUN mkdir -p /work \
    && printf 'PAYLOAD-9F3A\n' > /work/owned.txt \
    && chown 1000:1000 /work/owned.txt \
    && chmod 0600 /work/owned.txt
WORKDIR /app
COPY app/ /app/
RUN chmod 0755 /app/workload.sh /app/rootless/run.sh \
    && chown -R appuser:appuser /app/rootless
