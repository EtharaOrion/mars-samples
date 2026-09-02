#!/bin/bash
set -euo pipefail

/opt/holdout/corruption_bootstrap.sh

exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
