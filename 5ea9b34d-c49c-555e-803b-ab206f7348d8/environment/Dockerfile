FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends acl passwd adduser \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app/ /app/
RUN chmod 0755 /app/shared && chown root:root /app/shared
CMD ["sleep", "infinity"]
