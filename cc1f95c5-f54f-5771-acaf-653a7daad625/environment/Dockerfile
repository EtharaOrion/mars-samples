FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y git python3 python3-pytest && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app/ /app/
RUN sh /app/_setup.sh && rm -f /app/_setup.sh
CMD ["sleep", "infinity"]
