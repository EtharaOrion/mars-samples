FROM python:3.11-slim@sha256:272efc3f94bec901e2bc7a5c9984b3d113c317839edca2714c6a388b9476f8fc

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_ROOT_USER_ACTION=ignore
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        coreutils \
    && rm -rf /var/lib/apt/lists/*

# Isolated venv for verifier's pyyaml and the pinned pytest stack. The
# contract requires no runtime pypi access; every wheel is pulled at
# image build time and served from /opt/wheels at grader time.
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN pip install \
        pyyaml==6.0.2 \
        pytest==8.3.3 \
        pytest-rerunfailures==14.0 \
 && mkdir -p /opt/wheels \
 && pip wheel --no-deps --wheel-dir=/opt/wheels \
        pyyaml==6.0.2 \
        pytest==8.3.3 \
        pytest-rerunfailures==14.0

WORKDIR /workspace
COPY workspace /workspace

# Snapshot the observed initial pytest state for the agent to inspect.
# The seeded workflow argv (--reruns 1) plus the seeded workflow env
# (MAX_RETRIES=1) trip the test's convergence-floor assertion on the
# very first attempt, so the snapshot documents a deterministic failure
# rather than a flake.
RUN ( echo "=== initial simulated pytest run under the seeded workflow env + argv ===" > /workspace/observed_ci_output.txt \
   && ( cd /workspace \
        && rm -rf /tmp/flaky_convergence_state \
        && MAX_RETRIES=1 FLAKY_STATE_DIR=/tmp/flaky_convergence_state \
           pytest --reruns 1 tests/ >> /workspace/observed_ci_output.txt 2>&1 ; \
           echo "exit=$?" >> /workspace/observed_ci_output.txt ) ) || true

CMD ["/bin/bash"]
