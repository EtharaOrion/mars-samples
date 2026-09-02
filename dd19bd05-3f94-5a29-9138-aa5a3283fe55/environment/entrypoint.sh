#!/bin/bash
set -euo pipefail

mkdir -p /var/log/elasticsearch /var/lib/elasticsearch /var/log/supervisor
chown -R elasticsearch:elasticsearch /var/log/elasticsearch /var/lib/elasticsearch

SENTINEL=/opt/holdout/.bootstrap_done

if [ ! -f "$SENTINEL" ]; then
    bash /opt/holdout/corruption_bootstrap.sh bootstrap
    chmod 400 /opt/holdout/expected_four_index_content_hash.json \
              /opt/holdout/expected_four_index_docs.json \
              /opt/holdout/analytics_dangling_uuid.txt
    chown root:root /opt/holdout/expected_four_index_content_hash.json \
                    /opt/holdout/expected_four_index_docs.json \
                    /opt/holdout/analytics_dangling_uuid.txt
    touch "$SENTINEL"
    chmod 400 "$SENTINEL"
    chown root:root "$SENTINEL"
fi

exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
