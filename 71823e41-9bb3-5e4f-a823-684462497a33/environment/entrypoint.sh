#!/bin/bash
set -euo pipefail

mkdir -p /var/log/postgresql /var/log/pgbouncer /var/log/redis \
         /var/log/supervisor /var/run/pgbouncer /var/run/redis
chown -R postgres:postgres /var/log/postgresql /var/lib/postgresql
chown -R pgbouncer:pgbouncer /var/log/pgbouncer /var/run/pgbouncer
chown -R redis:redis /var/log/redis /var/lib/redis /var/run/redis

SENTINEL=/opt/holdout/.bootstrap_done

if [ ! -f "$SENTINEL" ]; then
    bash /opt/holdout/corruption_bootstrap.sh bootstrap
    chmod 400 /opt/holdout/expected_catalog_content_hash.json \
              /opt/holdout/expected_three_table_docs.json
    chown root:root /opt/holdout/expected_catalog_content_hash.json \
                    /opt/holdout/expected_three_table_docs.json
    touch "$SENTINEL"
    chmod 400 "$SENTINEL"
    chown root:root "$SENTINEL"
fi

exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
