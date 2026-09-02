FROM rust:1.90-bookworm@sha256:3914072ca0c3b8aad871db9169a651ccfce30cf58303e5d6f2db16d1d8a7e58f

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 openssl ca-certificates cmake curl \
    && rm -rf /var/lib/apt/lists/*

COPY https-mock /srv/https-mock

RUN mkdir -p /srv/https-mock/certs && cd /srv/https-mock/certs && \
    openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
        -keyout ca.key -out ca.pem \
        -subj "/CN=mars-mock-root-ca" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign" && \
    openssl req -new -newkey rsa:2048 -nodes \
        -keyout key.pem -out leaf.csr \
        -subj "/CN=localhost" && \
    printf "subjectAltName=DNS:localhost,IP:127.0.0.1\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n" > leaf.ext && \
    openssl x509 -req -in leaf.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out cert.pem -days 3650 -sha256 -extfile leaf.ext && \
    rm leaf.csr leaf.ext ca.srl && \
    chmod 644 key.pem ca.key

RUN cp /srv/https-mock/certs/ca.pem /usr/local/share/ca-certificates/mars-mock.crt \
    && update-ca-certificates

COPY workspace /workspace
WORKDIR /workspace

RUN cargo fetch
RUN mkdir -p .cargo && cargo vendor > .cargo/config.toml
RUN cargo build --release --workspace > /workspace/prebuild_log.txt 2>&1

RUN python3 /srv/https-mock/server.py > /tmp/mock.log 2>&1 & sleep 3 \
    && /workspace/target/release/target_binary /hello /world > /workspace/observed_panic.txt 2>&1 || true

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
