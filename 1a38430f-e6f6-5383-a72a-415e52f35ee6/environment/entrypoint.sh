#!/bin/bash
# entrypoint.sh: bring redis up, launch the drift-tick maintenance loop, drop
# to the agent shell.
set -u

CONF=/etc/redis/redis.conf
SOCK=/var/run/redis/redis.sock
TICK=/var/lib/redis/mutation_tick

mkdir -p /var/run/redis /var/lib/redis /var/log/redis
rm -f "$SOCK" 2>/dev/null || true

# Start redis in the background.
redis-server "$CONF" --daemonize yes

# Wait up to 15 seconds for the socket to appear.
for i in $(seq 1 75); do
    if [ -S "$SOCK" ]; then
        break
    fi
    sleep 0.2
done

# Prime mutation_tick so the grader sees a baseline value even before the
# first drift tick fires.
date +%s > "$TICK" 2>/dev/null || true

# The silent-drift maintenance loop.  This is the pinned mutation mechanism
# under Phase 0.5 sign-off: an entrypoint-launched background bash loop that
# invokes /usr/local/bin/drift_tick every 60 seconds and never involves cron
# or systemd.
bash -c 'while true ; do /usr/local/bin/drift_tick ; sleep 60 ; done' &
disown

# Drop to interactive bash for the agent seat.
exec /bin/bash
