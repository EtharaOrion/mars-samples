#!/bin/sh
set -eu
IMAGE_REF="${IMAGE_REF:-localhost:5050/widgetapp:v1}"
APP_DIR="${APP_DIR:-./app}"

docker build -q -t widgetapp:build "$APP_DIR" >/dev/null
docker tag widgetapp:build "localhost:5001/widgetapp:v1"
docker push "localhost:5001/widgetapp:v1" || true
