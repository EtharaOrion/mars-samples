#!/bin/bash
set -euo pipefail
docker run -d --name "$NAME" \
  --read-only \
  --tmpfs /var/cache/app:rw,mode=1777 \
  --user 65534:65534 \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  "$IMAGE" >/dev/null
