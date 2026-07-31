FROM rust:1-bookworm
ENV CARGO_NET_OFFLINE=true
WORKDIR /app
COPY app/ /app/
RUN cargo build --release && cargo test --no-run || true
CMD ["sleep","infinity"]
