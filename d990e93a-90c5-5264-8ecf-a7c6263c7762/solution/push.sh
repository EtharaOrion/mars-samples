#!/bin/sh
set -eu
IMAGE_REF="${IMAGE_REF:-localhost:5050/widgetapp:v1}"
REGISTRY_PORT="${REGISTRY_PORT:-5050}"
REG_NAME="${REG_NAME:-local-registry}"
APP_DIR="${APP_DIR:-./app}"

docker rm -f "$REG_NAME" >/dev/null 2>&1 || true
docker run -d --rm --name "$REG_NAME" -p "127.0.0.1:${REGISTRY_PORT}:5000" registry:2 >/dev/null

i=0
while [ "$i" -lt 40 ]; do
  if curl -fsS "http://localhost:${REGISTRY_PORT}/v2/" >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 0.3
done

docker build -q -t widgetapp:build "$APP_DIR" >/dev/null
docker tag widgetapp:build "$IMAGE_REF"
docker push "$IMAGE_REF" >/dev/null
echo "pushed ${IMAGE_REF} to local registry on port ${REGISTRY_PORT}"
