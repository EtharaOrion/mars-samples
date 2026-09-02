# README FOR AGENT -- nginx-mtls-forward-auth-single-service

Author three files under /workspace/:

  1. /workspace/nginx.conf
  2. /workspace/mime.types
  3. /workspace/reload.sh    (must be executable)

PKI is under /workspace/input/pki/ (see task instruction).
Upstream stub is at http://127.0.0.1:8080/ (already running).

Target listen ports:
  * :443 -> TLS 1.3 + mTLS + forward-auth + reverse proxy to 127.0.0.1:8080
  * :80  -> 301 redirect to https://<host><uri>

JSON access-log field set (must match exactly, no more no less):
  request_id, remote_addr, ts_iso8601, request_method, request_uri,
  http_host, status, body_bytes_sent, request_time_seconds,
  ssl_client_verify, ssl_client_s_dn, http_user_agent

Prohibited:
  * apt/pip/npm/cargo install
  * network fetch (curl to http/https, wget, git clone)
  * nginx -T dump-and-reflect
  * curl -k / --insecure
  * ssl_verify_client off / optional_no_ca
  * proxy_ssl_verify off
  * referencing any /dataset/ or /holdout/ path substring in authored files
  * pasting a canary token in any authored file
