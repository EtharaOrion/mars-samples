#!/usr/bin/env bash
# Supervisord post-start hook. Runs against the PERSISTENT vault instance
# (started by supervisord) after the daemon is reachable. Minimal job:
#   1. Wait for vault daemon to be reachable.
#   2. Unseal vault using the key from bootstrap-state.json.
#   3. Wait for vault to reach initialized+unsealed+active state.
#   4. Move bootstrap-state.json to init-holdout.json (root token stays alive;
#      tests/test.sh consumes root to issue the fresh repair-role token that
#      the agent uses, then revokes root, then emits boot_barrier.timestamp
#      that opens the D4 audit-log filter window).
#   5. Exit 0.
# Does NOT issue repair-role or audit-role tokens.
# Does NOT revoke root.
# Does NOT plant /workspace/.vault-token.
# Does NOT emit /var/lib/vault/boot_barrier.timestamp.
# All four of those actions happen in tests/test.sh so they land BELOW
# the D4 timestamp filter lower bound and are naturally excluded from
# the divergence check window.
set -euo pipefail

export VAULT_ADDR=http://127.0.0.1:8200
export HOME=/var/lib/vault

BOOTSTRAP_STATE=/var/lib/vault/bootstrap-state.json
INIT_HOLDOUT=/var/lib/vault/init-holdout.json

if [ -f "$INIT_HOLDOUT" ]; then
    exit 0
fi

if [ ! -f "$BOOTSTRAP_STATE" ]; then
    echo "vault_post_start: BOOTSTRAP_STATE missing at $BOOTSTRAP_STATE" >&2
    exit 1
fi

for _ in $(seq 1 60); do
    if curl -sf -o /dev/null http://127.0.0.1:8200/v1/sys/seal-status; then break; fi
    sleep 1
done

UNSEAL_KEY=$(jq -r .unseal_key "$BOOTSTRAP_STATE")
vault operator unseal "$UNSEAL_KEY" >/dev/null

READY=0
for _ in $(seq 1 180); do
    STATUS=$(curl -s http://127.0.0.1:8200/v1/sys/health 2>/dev/null || echo '{}')
    INITIALIZED=$(echo "$STATUS" | jq -r '.initialized')
    SEALED=$(echo "$STATUS" | jq -r '.sealed')
    STANDBY=$(echo "$STATUS" | jq -r '.standby')
    if [ "$INITIALIZED" = "true" ] && [ "$SEALED" = "false" ] && [ "$STANDBY" = "false" ]; then
        READY=1
        break
    fi
    sleep 1
done

if [ "$READY" != "1" ]; then
    echo "vault_post_start: vault did not reach initialized+unsealed+active within 180s" >&2
    exit 1
fi

cp "$BOOTSTRAP_STATE" "$INIT_HOLDOUT"
chown vault:vault "$INIT_HOLDOUT"
chmod 0600 "$INIT_HOLDOUT"

rm -f "$BOOTSTRAP_STATE"

exit 0
