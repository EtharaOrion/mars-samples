FROM --platform=linux/amd64 rust:1-bookworm
ENV CARGO_NET_OFFLINE=true
RUN rustup target add aarch64-unknown-linux-gnu \
 && apt-get update \
 && apt-get install -y gcc-aarch64-linux-gnu file \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app/ /app/
RUN cargo build --release || true
CMD ["sleep","infinity"]
