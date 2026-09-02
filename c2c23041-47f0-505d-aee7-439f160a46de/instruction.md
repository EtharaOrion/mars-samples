# nginx mTLS forward-auth single-service

You are inside a container with nginx-full, openssl, curl, python3, jq, and
coreutils on PATH. A public key infrastructure is baked under
`/workspace/input/pki/`:

  - `server.crt` / `server.key`         -- RSA-3072 server keypair (SAN=localhost)
  - `server-ca.crt`                     -- the root the verifier uses to trust
                                          your server cert
  - `client-ca.crt`                     -- TWO-cert PEM chain (root+intermediate)
                                          authorizing clients CN=svc-*,O=Ethara
  - `client-crl.pem`                    -- CRL revoking one client (svc-delta)
  - `clients/valid.{crt,key}`           -- CN=svc-alpha (fresh, not revoked)
  - `clients/expired.{crt,key}`         -- CN=svc-beta (validity ended pre-NOW)
  - `clients/unknown-ca.{crt,key}`      -- CN=svc-gamma (signed by an
                                          unrelated root NOT in client-ca.crt)
  - `clients/revoked.{crt,key}`         -- CN=svc-delta (fresh but on the CRL)

An upstream stub is pre-started on `http://127.0.0.1:8080/` serving
`/workspace/input/upstream/index.html` on `GET /` and echoing the incoming
request header block as `text/plain` on `GET /_echo_headers`. The upstream
is out of scope; you configure nginx in front of it.

## Author three files under `/workspace/`

  1. `/workspace/nginx.conf`
  2. `/workspace/mime.types`
  3. `/workspace/reload.sh`  (must be executable)

Together they must configure nginx to:

  - Terminate TLS 1.3 on `:443` using `server.crt` / `server.key`.
  - Require mutual client-certificate authentication against `client-ca.crt`
    with the correct chain-traversal depth for a root+intermediate bundle.
  - Consult `client-crl.pem` and reject revoked clients at handshake.
  - Gate every public request through an internal `auth_request` forward-auth
    subrequest that inspects the client subject.
  - Inject `X-Verified-Subject: $ssl_client_s_dn` into the upstream request.
  - Proxy the enriched request to `http://127.0.0.1:8080/`.
  - Emit JSON access-log lines at `/var/log/nginx/access.log` with the
    field set: `request_id, remote_addr, ts_iso8601, request_method,
    request_uri, http_host, status, body_bytes_sent, request_time_seconds,
    ssl_client_verify, ssl_client_s_dn, http_user_agent`.
  - Redirect `http://<any-host>/<any-path>` -> `https://<same-host>/<same-path>`
    with status `301` on `:80`.

`/workspace/reload.sh` must (a) install the two config files at
`/etc/nginx/nginx.conf` and `/etc/nginx/mime.types`, (b) invoke
`nginx -t -c /etc/nginx/nginx.conf` and fail loudly on nonzero, (c) start
nginx and wait for `:443` to bind, and (d) exit `0` on success.

## Grading

The verifier invokes `bash /workspace/reload.sh` from a shell rooted at
`/workspace/` with `LC_ALL=C`, waits for it to exit, re-checks
`nginx -t -c /etc/nginx/nginx.conf`, waits up to 5 seconds for `:443` to
bind, runs an 8-probe curl matrix against localhost, and reads the JSON
access-log window produced by the probes. The exact byte-truth for each
probe response and the JSON log record set are NOT disclosed here.

Rules:
  - Do not read `/dataset/` or the verifier's private holdout tree.
  - Do not `apt install` / `pip install` / `npm install` / `cargo install`
    or fetch anything over the network.
  - Do not paste a canary token, do not reference any `solution/` path.
