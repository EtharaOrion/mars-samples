#!/bin/sh
podman run --rm --userns=keep-id \
  -v /work:/mnt \
  -v /app/workload.sh:/mnt-workload:ro \
  alpine:3.20 sh /mnt-workload
