#!/bin/sh
set -eu
here="$(CDPATH= cd "$(dirname "$0")" && pwd)"
cd "$here"
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_SYSTEM=/dev/null
if [ ! -d .git ]; then
  git init -q .
  git config user.email forge@anubis.local
  git config user.name forge
fi
git add -A
export PRE_COMMIT_HOME="$here/.pccache"
exec pre-commit run --all-files
