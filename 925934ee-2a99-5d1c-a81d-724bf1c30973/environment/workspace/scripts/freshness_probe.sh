#!/bin/bash
# freshness_probe.sh -- called by the pipeline's verify stage to assert
# the cache the runner just pulled belongs to the current ISO week.
# Reads CI_ISO_WEEK from the environment and compares it against the
# week token recorded inside <cache_dir>/week_marker.txt. A missing
# marker or a week mismatch is a stale cache and exits non-zero.
set -eu

cache_dir="${1:-.gitlab-cache}"

if [ -z "${CI_ISO_WEEK:-}" ]; then
  echo "freshness_probe: CI_ISO_WEEK must be set by the runner" >&2
  exit 1
fi

marker_path="$cache_dir/week_marker.txt"
if [ ! -f "$marker_path" ]; then
  echo "FRESHNESS_PROBE_FAIL: no cache marker at $marker_path"
  exit 2
fi

recorded_week="$(cat "$marker_path")"
if [ "$recorded_week" = "$CI_ISO_WEEK" ]; then
  echo "FRESHNESS_PROBE_OK: cache week $recorded_week matches current $CI_ISO_WEEK"
  exit 0
else
  echo "FRESHNESS_PROBE_FAIL: cache week $recorded_week does not match current $CI_ISO_WEEK"
  exit 3
fi
