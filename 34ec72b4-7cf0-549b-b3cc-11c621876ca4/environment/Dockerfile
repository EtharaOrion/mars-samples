FROM python:3.11-slim@sha256:272efc3f94bec901e2bc7a5c9984b3d113c317839edca2714c6a388b9476f8fc

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_ROOT_USER_ACTION=ignore
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends patch git && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir 'setuptools>=68' wheel

WORKDIR /workspace

COPY myapp /workspace/myapp

COPY input.txt /workspace/input.txt

RUN pip install --no-deps --no-index --no-build-isolation -e /workspace/myapp > /workspace/prebuild_install_log.txt 2>&1

RUN /usr/local/bin/myapp --help > /workspace/observed_error.txt 2>&1 || true

CMD ["/bin/bash"]
