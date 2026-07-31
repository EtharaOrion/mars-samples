#!/bin/sh
set -e
cd /app
verify() {
  got=$(sha256sum "$1" | awk '{print $1}')
  if [ "$got" != "$2" ]; then
    echo "REDLINE: $1 was modified"
    exit 1
  fi
}
verify packages/core/src/index.js 20a6dc63c42ffdd4ca9e82ced23fefca0f1995e8dfd40533423e187f6002ddb4
verify packages/cli/src/index.js  02448ba5761c98de350f3652b92b330d987a60bce5be0506cb64548a25980b1b
verify packages/core/test.js      5d8ea865372df53ab486461b6b3a9a466f561565ee02217e92d571e253438b08
verify packages/cli/test.js       9db1f5ac5adce20f352017daaa75f04c47d8b803816a0100758ce8982636af8a
