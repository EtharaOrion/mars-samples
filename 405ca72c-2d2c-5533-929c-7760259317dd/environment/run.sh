#!/bin/bash
set -euo pipefail
docker run -d --name "$NAME" "$IMAGE" >/dev/null
