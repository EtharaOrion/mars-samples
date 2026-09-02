FROM eclipse-temurin:21-jdk-jammy@sha256:fe4f9ef764270df4c12c30e9db5498ceb5eaec1c0c3347964adf4acc2d9c3dda

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        curl \
        unzip \
        wget \
        python3 \
    && rm -rf /var/lib/apt/lists/*

# Provision a second JDK (17) alongside the base image's JDK 21 so
# Gradle's auto-detection can pick either as its toolchain and the
# release-target directive resolves against a genuine JDK 17.
RUN cd /opt && ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ]; then \
        JDK17_URL="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.13%2B11/OpenJDK17U-jdk_aarch64_linux_hotspot_17.0.13_11.tar.gz"; \
    else \
        JDK17_URL="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.13%2B11/OpenJDK17U-jdk_x64_linux_hotspot_17.0.13_11.tar.gz"; \
    fi && \
    wget -q "$JDK17_URL" -O jdk17.tar.gz && \
    tar xzf jdk17.tar.gz && \
    rm jdk17.tar.gz && \
    ln -s /opt/jdk-17.0.13+11 /opt/jdk-17

# Register both JDKs with Gradle's auto-detection via GRADLE_USER_HOME.
ENV JAVA21_HOME=/opt/java/openjdk
ENV JAVA17_HOME=/opt/jdk-17
ENV ORG_GRADLE_JAVA_INSTALLATIONS_PATHS=/opt/java/openjdk,/opt/jdk-17

# Pin Gradle 8.5 at the system PATH so the agent invokes `gradle` and
# not the (network-disabled) gradle wrapper download.
RUN cd /tmp && \
    curl -sL https://services.gradle.org/distributions/gradle-8.5-bin.zip -o gradle.zip && \
    mkdir -p /opt/gradle && \
    unzip -q gradle.zip -d /opt/gradle && \
    rm gradle.zip && \
    ln -s /opt/gradle/gradle-8.5/bin/gradle /usr/local/bin/gradle

RUN mkdir -p /workspace
WORKDIR /workspace
COPY workspace /workspace

# Snapshot the naive-attempt symptom the agent inspects at task start.
# Runs `gradle build` once in a scratch copy so the observed bytecode
# mismatch is captured without polluting the live /workspace tree.
RUN cp -a /workspace /tmp/probe \
 && (cd /tmp/probe && gradle --no-daemon --console=plain build 2>&1) > /workspace/observed_bytecode_mismatch.txt || true \
 && echo "" >> /workspace/observed_bytecode_mismatch.txt \
 && echo "=== javap -v on main class in scratch probe ===" >> /workspace/observed_bytecode_mismatch.txt \
 && (find /tmp/probe/build/classes/java/main -name '*.class' | head -1 | xargs -r -I{} sh -c 'javap -v "{}" 2>/dev/null | head -3') >> /workspace/observed_bytecode_mismatch.txt || true \
 && rm -rf /tmp/probe \
 && chmod -R a+rw /workspace

CMD ["/bin/bash"]
