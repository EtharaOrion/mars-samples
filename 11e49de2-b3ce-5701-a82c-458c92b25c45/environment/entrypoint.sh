#!/bin/bash
# Silent mutation loop: rotate /var/lib/postgresql/data/pg_hba.conf between
# trust and scram-sha-256 states every 90 seconds; touch
# /var/lib/postgresql/mutation_tick on every tick so the verifier can prove
# the loop was alive during the agent phase.  No cron and no systemd timer;
# the entrypoint-launched `while true; sleep 90; done` shell loop IS the
# mutation mechanism, pinned as an image build-time contract.
bash -c 'while true ; do /usr/local/bin/rotate_pg_hba ; sleep 90 ; done' &
disown
exec /bin/bash
