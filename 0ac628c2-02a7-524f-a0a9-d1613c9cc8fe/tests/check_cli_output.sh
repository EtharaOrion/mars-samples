#!/bin/sh
set -e
cd /app
# Grade a clean build: artifacts must be regenerated from source config.
rm -rf packages/core/dist packages/cli/dist node_modules packages/core/node_modules packages/cli/node_modules
pnpm install --offline --silent
pnpm -r build
test -f packages/core/dist/index.js
test -f packages/cli/dist/index.js
out=$(node packages/cli/dist/index.js)
expected="@app/cli: sum-of-squares(10) = 385 [core v2.0.0]"
if [ "$out" != "$expected" ]; then
  echo "BAD_OUTPUT: $out"
  exit 1
fi
pnpm -r test
