#!/bin/bash
set -euo pipefail

mkdir -p /var/log/app /var/log/supervisor /var/lib/prometheus
: > /var/log/app/audit.log
chmod 664 /var/log/app/audit.log
chown root:root /var/log/app/audit.log

exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
