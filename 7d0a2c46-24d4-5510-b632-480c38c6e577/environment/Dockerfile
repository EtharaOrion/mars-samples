FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        binutils \
        build-essential \
        ca-certificates \
        cmake \
        coreutils \
        gcc \
        libc6-dev \
        make \
        patchelf \
        python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY workspace /workspace

# Snapshot the observed symptom the agent sees at task start: a cold build
# and install succeed against the pinned CMakeLists.txt, but running the
# installed binary immediately fails with a shared-library-load error
# because the install rpath is empty. The captured symptom is a hint,
# never a substitute for actually fixing the CMakeLists.txt.
RUN ( set +e \
   && rm -rf /tmp/observed_build /tmp/observed_stage \
   && cmake -S /workspace -B /tmp/observed_build > /workspace/observed_symptom.txt 2>&1 \
   && cmake --build /tmp/observed_build >> /workspace/observed_symptom.txt 2>&1 \
   && cmake --install /tmp/observed_build --prefix /tmp/observed_stage >> /workspace/observed_symptom.txt 2>&1 \
   && printf '\n=== attempted run of installed myapp ===\n' >> /workspace/observed_symptom.txt \
   && env -i /tmp/observed_stage/bin/myapp >> /workspace/observed_symptom.txt 2>&1 \
   ; rm -rf /tmp/observed_build /tmp/observed_stage \
   ; true )

CMD ["/bin/bash"]
