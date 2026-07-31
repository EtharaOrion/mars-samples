FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y bash coreutils && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app/ /app/
RUN mkdir -p /opt/tools/bin \
 && cp /app/greet /opt/tools/bin/greet \
 && chmod 0755 /opt/tools/bin/greet \
 && rm -f /app/greet
CMD ["sleep", "infinity"]
