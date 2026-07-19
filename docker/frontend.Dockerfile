# Runs the Vite dev server with HMR — used by docker-compose.yml for local
# development. This is the default build target so existing `docker compose
# build`/`up` (no --target flag) keeps working unchanged.
FROM node:20-bullseye AS dev

WORKDIR /app

# Required to compile native optional dependencies for Rollup / esbuild
RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# Produces the static production bundle (frontend/dist). Only reached when
# building with --target production (or production's stage below, which
# depends on it) — docker-compose.yml's dev service never builds this far.
FROM node:20-bullseye AS builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ .

# Vite bakes VITE_* env vars into the bundle at build time, not read at
# container runtime — and frontend/.env is deliberately excluded from the
# Docker build context (.dockerignore), so npm run build would otherwise
# see neither VITE_API_BASE_URL nor VITE_APP_NAME and ship both as
# `undefined` (every API call pointed at the wrong origin, blank branding).
# docker-compose.prod.yml passes these as build args, sourced from the
# root .env (see .env.example) — the same two values frontend/.env.example
# documents, just also needed one level up for Compose's own ${...}
# substitution in build.args to reach them.
ARG VITE_API_BASE_URL
ARG VITE_APP_NAME
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_NAME=${VITE_APP_NAME}

RUN npm run build

# Serves the static build via nginx — no Node.js, no dev dependencies, no
# source maps of the toolchain, just the compiled assets. Used by
# docker-compose.prod.yml via `build.target: production`.
FROM nginx:1.27-alpine AS production

COPY docker/nginx.frontend.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx:alpine ships an unprivileged "nginx" user and already-writable
# runtime dirs for it; nginx-unprivileged patterns aren't needed here since
# the stock image supports running as non-root out of the box.
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/run \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid
USER nginx

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
