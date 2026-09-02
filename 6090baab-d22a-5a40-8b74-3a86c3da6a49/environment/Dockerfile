FROM node:20-slim@sha256:3d0f05455dea2c82e2f76e7e2543964c30f6b7d673fc1a83286736d44fe4c41c

ENV DEBIAN_FRONTEND=noninteractive
ENV NPM_CONFIG_UPDATE_NOTIFIER=false
ENV NPM_CONFIG_FUND=false
ENV NPM_CONFIG_AUDIT=false

WORKDIR /workspace/app

COPY package.json /workspace/app/package.json
COPY tsconfig.json /workspace/app/tsconfig.json
COPY src /workspace/app/src

RUN npm install --no-save --prefer-offline --no-audit --no-fund typescript@5.7.2 \
  > /workspace/prebuild_install_log.txt 2>&1

RUN /workspace/app/node_modules/.bin/tsc --project /workspace/app/tsconfig.json \
  > /workspace/observed_tsc.txt 2>&1 || true

RUN node /workspace/app/dist/index.js \
  > /workspace/observed_node.txt 2>&1 || true

CMD ["/bin/bash"]
