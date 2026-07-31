FROM node:22-bookworm-slim
RUN corepack enable && corepack prepare pnpm@9.12.3 --activate
ENV CI=true
WORKDIR /app
COPY app/ /app/
CMD ["sleep","infinity"]
