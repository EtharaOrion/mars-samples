FROM eclipse-temurin:17-jdk-jammy@sha256:723151f3fc88ca2060153ee08ab8dbbea7983d6ed6f2622fe440acf178737c94

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV MAVEN_OPTS="-Dmaven.repo.local=/root/.m2/repository -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        coreutils \
        maven \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Isolated venv for verifier's pyyaml (contract requires no runtime pypi access).
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN pip install pyyaml==6.0.2 \
 && mkdir -p /opt/wheelhouse \
 && pip wheel --no-deps --wheel-dir=/opt/wheelhouse pyyaml==6.0.2

WORKDIR /workspace
COPY workspace /workspace

# Pre-warm the Maven local repository so runtime pipelines can execute
# with --offline. The verifier is contractually forbidden from reaching
# the network at grading time.
#
# The initial checkstyle:check is expected to fail on the two seeded
# violations; the javadoc:javadoc pre-warm is expected to succeed
# because in the initial (unmodified) source the LedgerFormatter import
# is still present and the {@link} reference resolves. The `|| true`
# guards swallow the checkstyle exit code so subsequent Docker layers
# still populate /root/.m2/repository with the javadoc plugin bytes.
RUN cd /workspace \
 && mvn -B -e -DskipTests dependency:go-offline || true \
 && mvn -B -e checkstyle:check                    || true \
 && mvn -B -e -DskipTests package                 || true \
 && mvn -B -e javadoc:javadoc                     || true

# Snapshot the observed initial lint state for the agent to inspect.
RUN ( echo "=== initial mvn -o checkstyle:check exit + output ===" > /workspace/observed_lint_output.txt \
   && ( cd /workspace && mvn -o -B -e checkstyle:check >> /workspace/observed_lint_output.txt 2>&1 ; echo "exit=$?" >> /workspace/observed_lint_output.txt ) ) || true

CMD ["/bin/bash"]
