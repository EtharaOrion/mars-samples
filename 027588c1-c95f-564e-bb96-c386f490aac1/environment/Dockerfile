FROM node:20-slim@sha256:3d0f05455dea2c82e2f76e7e2543964c30f6b7d673fc1a83286736d44fe4c41c

ENV DEBIAN_FRONTEND=noninteractive
ENV NPM_CONFIG_UPDATE_NOTIFIER=false
ENV NPM_CONFIG_FUND=false
ENV NPM_CONFIG_AUDIT=false

WORKDIR /workspace

COPY workspace/app /workspace/app
COPY workspace/consumers /workspace/consumers

RUN cd /workspace/app \
  && npm install --no-save --prefer-offline --no-audit --no-fund \
       typescript@5.7.2 @types/node@20.17.10 \
  > /workspace/prebuild_install_log.txt 2>&1

RUN mkdir -p /workspace/consumers/node_modules/@pkg \
  && ln -s /workspace/app /workspace/consumers/node_modules/@pkg/dual

RUN cd /workspace/app \
  && ./node_modules/.bin/tsc -p tsconfig.esm.json \
  > /workspace/observed_build.txt 2>&1 || true

RUN cd /workspace/consumers \
  && node /workspace/consumers/esm-consumer.mjs \
  > /workspace/observed_esm.txt 2>&1 || true

RUN cd /workspace/consumers \
  && node /workspace/consumers/cjs-consumer.cjs \
  > /workspace/observed_cjs.txt 2>&1 || true

CMD ["/bin/bash"]
