#!/bin/bash
# populate_cache.sh -- called by the pipeline's populate stage to seed
# the cache directory with a week-marker file that records the ISO week
# of the current run. Reads CI_ISO_WEEK from the environment (set by
# the GitLab runner at job time) and writes it verbatim into
# <cache_dir>/week_marker.txt.
set -eu

cache_dir="${1:-.gitlab-cache}"
mkdir -p "$cache_dir"

if [ -z "${CI_ISO_WEEK:-}" ]; then
  echo "populate_cache: CI_ISO_WEEK must be set by the runner" >&2
  exit 1
fi

echo "$CI_ISO_WEEK" > "$cache_dir/week_marker.txt"
echo "populate_cache: wrote week marker for $CI_ISO_WEEK to $cache_dir/week_marker.txt"
