FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        git \
        gzip \
        jq \
        python3 \
        python3-yaml \
        tar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY workspace /workspace
COPY cache_seed /tmp/cache_seed

# Seed a stale prior-week cache tarball at /cache/main.tar.gz. The
# naive `key: $CI_COMMIT_REF_SLUG` in .gitlab-ci.yml resolves to
# `main` under the pipeline the grader simulates, so a naive fix
# still pulls this tarball and its stale week marker fails the
# freshness probe.
RUN mkdir -p /cache \
 && bash /tmp/cache_seed/seed_stale_cache.sh /cache \
 && rm -rf /tmp/cache_seed

# Snapshot the naive-attempt symptom the agent inspects at task start.
# Copies the workspace to a scratch directory, simulates a current-week
# pipeline run against the unedited .gitlab-ci.yml with the stale
# cache in place, and captures the freshness_probe failure the agent
# must defeat. Uses python3 with PyYAML for the tiny simulator so the
# snapshot is deterministic and does not depend on a live gitlab
# runner. Writes to /workspace/observed_naive_attempt.txt; the live
# /workspace tree is not polluted because the simulator runs in a
# scratch copy at /tmp/probe.
RUN cp -a /workspace /tmp/probe \
 && mkdir -p /tmp/probe_cache \
 && cp /cache/main.tar.gz /tmp/probe_cache/main.tar.gz \
 && python3 - <<'PROBE' > /workspace/observed_naive_attempt.txt 2>&1 || true
import os, subprocess, sys, tarfile, yaml, string
WS = "/tmp/probe"
CACHE = "/tmp/probe_cache"
env = {
    "CI_COMMIT_REF_SLUG": "main",
    "CI_ISO_WEEK": "2026-W35",
    "PATH": os.environ["PATH"],
    "HOME": "/root",
    "LC_ALL": "C",
    "LANG": "C",
}
doc = yaml.safe_load(open(os.path.join(WS, ".gitlab-ci.yml")))
stages = doc.get("stages", [])
jobs = [(n, c) for n, c in doc.items() if isinstance(c, dict) and "script" in c]
jobs.sort(key=lambda kv: stages.index(kv[1].get("stage", stages[0])) if stages else 0)
print("=== NAIVE-CONFIG SIMULATION: CI_COMMIT_REF_SLUG=main CI_ISO_WEEK=2026-W35 ===")
for name, cfg in jobs:
    tmpl = cfg.get("cache", {}).get("key", "")
    key = string.Template(tmpl).safe_substitute(env)
    print(f"--- job: {name}  resolved_cache_key: {key!r} ---")
    tar = os.path.join(CACHE, key + ".tar.gz")
    if os.path.exists(tar) and cfg.get("cache", {}).get("policy", "pull-push") in ("pull", "pull-push"):
        print(f"cache HIT at {tar}, extracting")
        with tarfile.open(tar) as t:
            t.extractall(WS)
    else:
        print(f"cache MISS for {tar}")
    for cmd in cfg["script"]:
        p = subprocess.run(["bash", "-c", cmd], cwd=WS, env=env, capture_output=True, text=True)
        sys.stdout.write(p.stdout)
        sys.stderr.write(p.stderr)
        if p.returncode != 0:
            print(f"[job {name} exited {p.returncode}]")
            break
PROBE
RUN rm -rf /tmp/probe /tmp/probe_cache \
 && chmod -R a+rw /workspace

CMD ["/bin/bash"]
