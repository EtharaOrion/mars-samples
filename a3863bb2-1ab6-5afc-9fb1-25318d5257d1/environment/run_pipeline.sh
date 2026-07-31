#!/bin/sh
set -eu
NESTED_CTX="${NESTED_CTX:-./nested}"
OUT_DIR="${OUT_DIR:-./out}"
NESTED_IMAGE="${NESTED_IMAGE:-star26-nested:v1}"
NESTED_NAME="${NESTED_NAME:-star26-nested-ctr}"
mkdir -p "$OUT_DIR"
docker run --rm \
  -v "$NESTED_CTX":/nested:ro \
  -v "$OUT_DIR":/out \
  -e NESTED_IMAGE -e NESTED_NAME \
  alpine:3.20 sh -c '
    docker build -q -t "$NESTED_IMAGE" /nested >/dev/null
    docker rm -f "$NESTED_NAME" >/dev/null 2>&1 || true
    docker run --name "$NESTED_NAME" "$NESTED_IMAGE" > /out/result.txt
  '
