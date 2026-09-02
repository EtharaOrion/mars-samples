#!/usr/bin/env bash
# inv-30 container entrypoint. Runs bootstrap once (idempotent by state-file check),
# then execs supervisord which manages vault, postgres, nginx, webapp.
set -euo pipefail
if [ ! -f /var/lib/vault/boot_barrier.timestamp ]; then
    /opt/bootstrap.sh
fi
exec "$@"
