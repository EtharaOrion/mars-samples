#!/bin/bash
# seed_stale_cache.sh -- called at image-build time to seed a stale
# prior-week cache tarball into the runner cache root. The tarball
# is named to match the naive cache key `$CI_COMMIT_REF_SLUG` alone
# resolving to the branch `main`, so a pipeline whose cache key does
# not further isolate on the ISO week will pull this stale tarball
# and its week-marker will fail the freshness probe.
set -eu

cache_root="${1:-/cache}"
stale_week="2026-W30"

mkdir -p "$cache_root"

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

# Reproduce the on-disk layout the runner's cache tarball wraps:
# a `.gitlab-cache/` directory holding the week marker.
mkdir -p "$scratch/.gitlab-cache"
echo "$stale_week" > "$scratch/.gitlab-cache/week_marker.txt"

# The naive cache key `$CI_COMMIT_REF_SLUG` resolves to `main` under
# the pipeline the grader simulates, so the stale tarball must be
# stored at `<cache_root>/main.tar.gz` for the naive fix to still
# find it and fail freshness.
(cd "$scratch" && tar -czf "$cache_root/main.tar.gz" .gitlab-cache)

echo "seeded stale cache for week $stale_week at $cache_root/main.tar.gz"
