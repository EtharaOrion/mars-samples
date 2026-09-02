# mars-ci-gitlab-cache-key-cross-branch-stale-v2 workspace

This workspace is a small GitLab CI project with a two-job pipeline
defined in `.gitlab-ci.yml`:

    populate   (stage: cache_populate)   writes a week marker into
                                         .gitlab-cache/ that records
                                         the ISO week of the run.
    verify     (stage: verify_freshness) pulls the cache back and runs
                                         scripts/freshness_probe.sh to
                                         assert the marker matches the
                                         current ISO week.

The GitLab runner exposes two predefined variables to every job:

    CI_COMMIT_REF_SLUG   the branch slug of the pipeline
    CI_ISO_WEEK          the ISO week token of the pipeline
                         (e.g. "2026-W35"), derived from the pipeline
                         creation timestamp by the runner

The `.gitlab-cache/` directory is treated as the cache path by both
jobs. The cache tarball for a given key is stored at
`/cache/<resolved_key>.tar.gz` on the runner and pulled/pushed by the
runner between jobs and across pipelines.

The task ships with `observed_naive_attempt.txt`, a log of what the
current cache configuration produces when a stale cache tarball from
a prior ISO week is already present on the runner and a new
current-week pipeline runs. The freshness probe fails on that log
because the current cache key does not isolate stale prior-week
bytes from the current-week pipeline. That is the failure your fix
must defeat.
