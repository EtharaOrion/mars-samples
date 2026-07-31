#!/bin/sh
podman --storage-driver=vfs run --rm --network=none --userns=keep-id \
  -v /work:/mnt \
  -v /app/workload.sh:/mnt-workload:ro \
  alpine:3.20 sh /mnt-workload
