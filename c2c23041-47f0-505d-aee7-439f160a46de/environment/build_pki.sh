#!/usr/bin/env bash
set -euo pipefail

PKI=/workspace/input/pki
mkdir -p "$PKI/clients" "$PKI/_ca"
cd "$PKI/_ca"

# Deterministic openssl config
cat > openssl.cnf <<'CFG'
[req]
distinguished_name = dn
prompt = no
[dn]
CFG

# --- Ethara test ROOT CA ---
openssl genrsa -out root.key 3072 2>/dev/null
cat > root.cnf <<'CFG'
[req]
distinguished_name = dn
prompt = no
x509_extensions = v3_ca
[dn]
O  = Ethara
CN = Ethara Test Root CA
[v3_ca]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
CFG
openssl req -x509 -new -key root.key -out root.crt \
    -config root.cnf -set_serial 0x1001 \
    -days 3650 -sha256 2>/dev/null

# --- Ethara test INTERMEDIATE CA (signed by root) ---
openssl genrsa -out inter.key 3072 2>/dev/null
cat > inter.cnf <<'CFG'
[req]
distinguished_name = dn
prompt = no
req_extensions = v3_ca
[dn]
O  = Ethara
CN = Ethara Test Intermediate CA
[v3_ca]
basicConstraints = critical, CA:TRUE, pathlen:0
keyUsage = critical, keyCertSign, cRLSign
CFG
openssl req -new -key inter.key -out inter.csr -config inter.cnf 2>/dev/null
openssl x509 -req -in inter.csr -CA root.crt -CAkey root.key \
    -set_serial 0x2001 -days 3650 -sha256 \
    -extfile inter.cnf -extensions v3_ca -out inter.crt 2>/dev/null

# --- SERVER cert (signed by root, SAN=localhost) ---
openssl genrsa -out "$PKI/server.key" 3072 2>/dev/null
cat > srv.cnf <<'CFG'
[req]
distinguished_name = dn
prompt = no
req_extensions = v3_req
[dn]
O  = Ethara
CN = localhost
[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = DNS:localhost
CFG
openssl req -new -key "$PKI/server.key" -out srv.csr -config srv.cnf 2>/dev/null
openssl x509 -req -in srv.csr -CA root.crt -CAkey root.key \
    -set_serial 0x3001 -days 3650 -sha256 \
    -extfile srv.cnf -extensions v3_req -out "$PKI/server.crt" 2>/dev/null

# server-ca.crt = the trust anchor the VERIFIER uses to trust server.crt
cp root.crt "$PKI/server-ca.crt"

# client-ca.crt = concatenated root+intermediate chain (agent must use
# ssl_verify_depth 2 to traverse it)
cat root.crt inter.crt > "$PKI/client-ca.crt"

# --- CLIENT: valid (CN=svc-alpha, signed by intermediate) ---
issue_client() {
    local name="$1"; local cn="$2"; local serial="$3"
    local signer_crt="$4"; local signer_key="$5"; local days="$6"
    openssl genrsa -out "$PKI/clients/${name}.key" 3072 2>/dev/null
    cat > "${name}.cnf" <<CFG
[req]
distinguished_name = dn
prompt = no
req_extensions = v3_client
[dn]
O  = Ethara
CN = ${cn}
[v3_client]
basicConstraints = CA:FALSE
keyUsage = digitalSignature
extendedKeyUsage = clientAuth
CFG
    openssl req -new -key "$PKI/clients/${name}.key" -out "${name}.csr" \
        -config "${name}.cnf" 2>/dev/null
    openssl x509 -req -in "${name}.csr" -CA "${signer_crt}" -CAkey "${signer_key}" \
        -set_serial "${serial}" -days "${days}" -sha256 \
        -extfile "${name}.cnf" -extensions v3_client \
        -out "$PKI/clients/${name}.crt" 2>/dev/null
}

issue_client valid       svc-alpha 0x4001 inter.crt inter.key 3650

# --- CLIENT: expired (CN=svc-beta) ---
# Signed via `openssl ca` with pinned -startdate/-enddate (UTCTime,
# YYMMDDHHMMSSZ). The prior authoring pass used `openssl x509 -req
# -not_before/-not_after`, but those flags were only added in openssl
# >= 3.2; bookworm ships openssl 3.0.20 which supports -startdate/
# -enddate on the `openssl ca` subcommand instead. This alternative
# preserves the pinned validity window (2020-01-01 to 2020-06-01) and
# the pinned serial 0x4002. Bug discovered at Phase 2 docker build;
# see seed/bundle_derivation.yaml canonical_derivation_drift_note.
openssl genrsa -out "$PKI/clients/expired.key" 3072 2>/dev/null
cat > expired.cnf <<'CFG'
[req]
distinguished_name = dn
prompt = no
req_extensions = v3_client
[dn]
O  = Ethara
CN = svc-beta
[v3_client]
basicConstraints = CA:FALSE
keyUsage = digitalSignature
extendedKeyUsage = clientAuth
CFG
openssl req -new -key "$PKI/clients/expired.key" -out expired.csr \
    -config expired.cnf 2>/dev/null

# Minimal isolated CA DB rooted at the intermediate CA so `openssl ca`
# honours -startdate/-enddate; ca_db_expired/ avoids colliding with the
# CRL-signing DB set up later at ca_db/. Pinned serial 4002 (= 0x4002).
mkdir -p ca_db_expired
: > ca_db_expired/index.txt
echo '4002' > ca_db_expired/serial
cat > ca_expired.cnf <<'CFG'
[ca]
default_ca = ca_expired
[ca_expired]
dir              = .
database         = ./ca_db_expired/index.txt
serial           = ./ca_db_expired/serial
new_certs_dir    = ./ca_db_expired
certificate      = ./inter.crt
private_key      = ./inter.key
default_md       = sha256
default_days     = 3650
policy           = pol_any
copy_extensions  = copy
x509_extensions  = v3_client_local
[pol_any]
organizationName       = supplied
commonName             = supplied
[v3_client_local]
basicConstraints = CA:FALSE
keyUsage = digitalSignature
extendedKeyUsage = clientAuth
CFG
openssl ca -config ca_expired.cnf -batch -notext -in expired.csr \
    -startdate 200101000000Z -enddate 200601000000Z \
    -out "$PKI/clients/expired.crt" 2>/dev/null

# --- CLIENT: unknown-ca (CN=svc-gamma, signed by a DIFFERENT root not in
#     client-ca.crt trust store) ---
openssl genrsa -out other_root.key 3072 2>/dev/null
cat > other_root.cnf <<'CFG'
[req]
distinguished_name = dn
prompt = no
x509_extensions = v3_ca
[dn]
O  = OtherOrg
CN = Other Test Root
[v3_ca]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
CFG
openssl req -x509 -new -key other_root.key -out other_root.crt \
    -config other_root.cnf -set_serial 0x9001 -days 3650 -sha256 2>/dev/null
issue_client unknown-ca svc-gamma 0x4003 other_root.crt other_root.key 3650

# --- CLIENT: revoked (CN=svc-delta, signed by intermediate, then revoked) ---
issue_client revoked svc-delta 0x4004 inter.crt inter.key 3650

# --- Generate a CRL that revokes svc-delta ---
mkdir -p ca_db
: > ca_db/index.txt
echo '01' > ca_db/serial
echo '01' > ca_db/crlnumber
cat > ca.cnf <<'CFG'
[ca]
default_ca = the_ca
[the_ca]
dir              = .
database         = ./ca_db/index.txt
serial           = ./ca_db/serial
crlnumber        = ./ca_db/crlnumber
new_certs_dir    = ./ca_db
certificate      = ./inter.crt
private_key      = ./inter.key
default_md       = sha256
default_crl_days = 3650
policy           = pol_any
[pol_any]
organizationName       = supplied
commonName             = supplied
CFG
# Mark the revoked client cert as revoked in the CA index
openssl ca -config ca.cnf -revoke "$PKI/clients/revoked.crt" 2>/dev/null || true
openssl ca -config ca.cnf -gencrl -out inter-crl.pem 2>/dev/null

# --- Root CA CRL (empty, needed to complete nginx ssl_crl chain check) ---
# nginx requires a CRL for EVERY issuer in the client-ca chain when
# ssl_crl is set; missing the root CRL yields "unable to get certificate
# CRL" errors during TLS handshake for otherwise-valid certs. Bug
# discovered at Phase 2 reference-solve trial; see
# seed/bundle_derivation.yaml canonical_derivation_drift_note.
mkdir -p ca_db_root
: > ca_db_root/index.txt
echo '01' > ca_db_root/serial
echo '01' > ca_db_root/crlnumber
cat > ca_root.cnf <<'CFG'
[ca]
default_ca = the_root_ca
[the_root_ca]
dir              = .
database         = ./ca_db_root/index.txt
serial           = ./ca_db_root/serial
crlnumber        = ./ca_db_root/crlnumber
new_certs_dir    = ./ca_db_root
certificate      = ./root.crt
private_key      = ./root.key
default_md       = sha256
default_crl_days = 3650
policy           = pol_root
[pol_root]
organizationName       = supplied
commonName             = supplied
CFG
openssl ca -config ca_root.cnf -gencrl -out root-crl.pem 2>/dev/null

# Concatenate root CRL + intermediate CRL into the CRL bundle nginx uses.
cat root-crl.pem inter-crl.pem > "$PKI/client-crl.pem"

# --- Fixup permissions ---
chmod 644 "$PKI"/*.crt "$PKI"/*.pem "$PKI"/clients/*.crt
chmod 640 "$PKI"/*.key "$PKI"/clients/*.key
chown -R root:root "$PKI"

# Clean up build state; keep only the artifacts the agent + verifier need
rm -rf "$PKI/_ca"
