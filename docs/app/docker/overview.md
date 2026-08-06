# Docker Overview

---

## Services

| Service | Image / build | Purpose |
|---|---|---|
| `postgres` | `postgres:15` | Primary database |
| `redis` | `redis:7` | Cache, rate limits, lockout counters, refresh-token jti registry, single-use tokens, taskiq broker |
| `qdrant` | `qdrant/qdrant` | ManifestCV vector store for career knowledge chunk embeddings. Included in dev, local-prod, and prod. No healthcheck: the image ships neither `curl` nor `wget` to probe its own HTTP API with, so `backend` depends on it with the default `service_started` condition rather than `service_healthy` |
| `backend` | `docker/backend.Dockerfile` | FastAPI app (uvicorn). Also bundles `tectonic` (LaTeX engine) for PDF resume compilation. See [Document Generation](../document-generation/overview.md) |
| `frontend` | `docker/frontend.Dockerfile` (`dev` target locally, `production` target in prod) | React SPA. Vite dev server locally, nginx-served static build in prod |
| `taskiq_worker` | `docker/backend.Dockerfile` (same image as `backend`, different `command:`) | Consumes the email-sending task queue. See [Background Workers](../../mystic_auth/background-workers/taskiq.md) |
| `alembic` | `docker/backend.Dockerfile` (same image, one-shot) | Runs `alembic upgrade head` then exits. Applies both mystic-auth's inherited migrations and ManifestCV's own four. `backend`/`taskiq_worker` wait on its success |
| `bugsink` | `bugsink/bugsink:2` | Self-hosted error monitoring. Starts by default with `docker compose up` (matches upstream's own template default). See [Error Monitoring](../../mystic_auth/error-monitoring/overview.md) |
| `bugsink-seed` | `bugsink/bugsink:2` (same image, one-shot) | Runs once after `bugsink` reports healthy, then exits. Idempotently seeds a default Team + Project and writes the resulting DSN into the shared `bugsink_dsn` volume, which `backend`/`frontend` read at startup (bounded wait, gated on `BUGSINK_SUPERUSER_EMAIL`). See [Error Monitoring](../../mystic_auth/error-monitoring/overview.md) |

`backend`, `taskiq_worker`, and `alembic` all build from the **same** `docker/backend.Dockerfile` image with different `command:` overrides. Keeps dependency versions and application code identical across all three roles by construction. `bugsink` and `bugsink-seed` share the same relationship using `bugsink/bugsink:2`.

---

## Dockerfiles

- **`docker/backend.Dockerfile`**: two-stage build. A `builder` stage compiles native dependencies (`gcc`, `libpq-dev`) into an isolated venv. The runtime stage is `python:3.14.6-slim` with `libpq5` plus a statically-linked `tectonic` binary (fetched at build time, not full TeX Live, several GB smaller), running as a non-root `app` user. Ships a `HEALTHCHECK` against `/health/ready` as a fallback for when the image runs outside Compose.
- **`docker/frontend.Dockerfile`**: three stages: `dev` (default target, `node:22.22.0-bullseye`, Vite dev server with HMR, port 5173), `builder` (compiles the production bundle), `production` (`nginx:1.27-alpine` serving the static build as a non-root `nginx` user, port 80, `HEALTHCHECK` via `wget`). The `builder` stage takes `VITE_API_BASE_URL`/`VITE_APP_NAME`/`VITE_SENTRY_DSN`/`VITE_SENTRY_ENVIRONMENT` as build `ARG`s. Vite bakes them into the bundle at build time, and this stage has no bind-mounted `.env` to read them from, so without these args every production build would ship them as `undefined`. `docker-compose.prod.yml`/`docker-compose.local-prod.yml` pass them through as `build.args`, sourced from root `.env` via Compose's own `${VAR}` interpolation, the same file the dev server reads directly (see [Deployment Guide: production](../deployment/guide.md)).
- **`docker/nginx.frontend.conf`**: SPA fallback to `index.html`, gzip, security headers. Its CSP has no `frame-src` override, so `default-src 'self'` governs framing by fallback. The resume template preview `<iframe>` (see [Document Generation](../document-generation/overview.md)) doesn't need one, since it embeds a same-origin `blob:` object URL built client-side from an axios-fetched response, not a direct `<iframe src>` pointing at the backend's different origin. No HSTS at this layer, by design, since TLS terminates in front of this container (Caddy on `docker-compose.prod.yml`, Cloudflare's own edge on `docker-compose.local-prod.yml`), not here.

---

## Dev vs. Local-prod vs. Prod compose

| | `docker-compose.yml` (dev) | `docker-compose.local-prod.yml` | `docker-compose.prod.yml` |
|---|---|---|---|
| Frontend | Vite dev server, HMR, bind-mounted source | nginx serving the baked-in static build | nginx serving the baked-in static build |
| Backend/worker | `--reload`, bind-mounted `./backend:/app`. `backend` additionally mounts `.:/repo` and `frontend` mounts `./tests/frontend:/tests/frontend` + `.:/repo` so `docker compose exec` can run the top-level test suites | No reload, code baked into the image | No reload, code baked into the image |
| Restart policy | `restart: always` on postgres/redis/qdrant/bugsink (backend/frontend/worker/alembic/bugsink-seed have none) | `unless-stopped` on every long-running service | `unless-stopped` on every long-running service |
| Ports exposed | 5433 (postgres), 6380 (redis), 6333 (qdrant), 8000 (backend), 5173 (frontend), 8010 (bugsink, mapped from its own internal 8000) all published to host. Non-default DB/cache host ports deliberately chosen to dodge the common local 5432/6379 collision. Containers still reach each other at `postgres:5432`/`redis:6379`/`qdrant:6333` over the Docker network regardless | 8000 (backend), 80 (frontend), and 8010 (bugsink, `127.0.0.1` only) published for local debugging. Qdrant is internal only at `qdrant:6333`. `cloudflared` needs no inbound port at all. It opens an outbound tunnel | Nothing published except `caddy`'s 80/443. `postgres`/`redis`/`qdrant`/`backend`/`frontend`/`bugsink` are reachable only container-to-container |
| Public entrypoint | None (local only) | `cloudflared`, outbound tunnel to Cloudflare's edge, TLS terminates there | `caddy`, automatic Let's Encrypt TLS via `PUBLIC_DOMAIN`/`ACME_EMAIL`, reverse-proxies to `frontend:80` |
| `backend`/`taskiq_worker` startup gate | `postgres`/`redis` healthy, `qdrant` started, `alembic: service_completed_successfully` | Same | Same |

See [Deployment Guide](../deployment/guide.md) for when to use which of the three files.

---

## Day-to-day: `dev-up` helpers

`./scripts/docker/dev-up.sh` / `.\scripts\docker\dev-up.ps1` / `scripts\docker\dev-up.cmd`: upstream-owned wrappers around `docker compose up -d`. They poll long-running services until healthy, then tail fresh `backend`/`frontend`/`taskiq_worker` logs only so Postgres, Redis, Bugsink, and Alembic startup noise stays out of the way. Recommended over plain `docker compose up` for day-to-day work. See [mystic-auth's Docker overview](../../mystic_auth/docker/overview.md#day-to-day-dev-up-helpers) and root README's [Run the App](../../../README.md#-run-the-app).

---

## Test suite mounts

`backend` mounts the whole repo root additionally (`.:/repo`), and `frontend` mounts `./tests/frontend:/tests/frontend` + `.:/repo`: both let `docker compose exec` run the top-level `tests/backend/` and `tests/frontend/` suites from inside the Docker network (reaching Postgres, Redis, and Qdrant via their container hostnames) without needing a host-side Python/Node environment. See [Testing Overview](../testing/overview.md) ("Running" under each suite) for the exact commands.

---

## Healthchecks

| Service | Check | Notes |
|---|---|---|
| `postgres` | `pg_isready` | |
| `redis` | `redis-cli ping` (with `-a` if `REDIS_PASSWORD` is set) | |
| `qdrant` | none | See Services table above |
| `backend` | `GET /health/ready` via a Python one-liner (no curl in the slim image) | Confirms DB + Redis connectivity, not just process liveness |
| `frontend` (prod) | `wget` against `/` | |
| `frontend` (dev) | none | Acceptable for local dev, since Vite's own dev server failure is immediately visible in the terminal |
| `taskiq_worker` | greps `/proc/*/cmdline` for `taskiq` | Overrides the inherited HTTP healthcheck from `backend.Dockerfile`, since the worker serves no HTTP and would otherwise always report unhealthy |
| `alembic` | none | One-shot; `service_completed_successfully` is the signal other services wait on, not a healthcheck |
| `bugsink-seed` | none | One-shot, same reasoning as `alembic`: waits on `bugsink: service_healthy` rather than exposing its own check |

---

## Validation results

Ran `docker compose up --build` (dev compose) from the repo root after vendoring mystic-auth's latest core and wiring ManifestCV's own domains on top, and verified the merged stack end-to-end:

- All services (`postgres`, `redis`, `qdrant`, `backend`, `taskiq_worker`, `frontend`, `bugsink`, `bugsink-seed`) reached a running state, with `postgres`, `redis`, `backend`, `taskiq_worker`, `bugsink` reporting `healthy` on their respective healthchecks.
- `alembic` ran the full migration chain cleanly in one pass. `\dt` against the running Postgres confirmed all inherited tables plus `career_knowledge_bases`, `resume_drafts`, `resume_documents`, `application_records`.
- `GET /` returned `{"message": "Welcome to ManifestCV!"}`, and `GET /health/ready` returned `{"status":"ok","checks":{"database":"ok","redis":"ok"}}`.
- The full route inventory (`GET /openapi.json`) confirmed all four ManifestCV route groups mounted alongside every inherited mystic-auth route.
- `curl http://localhost:6333/collections` confirmed the `career_knowledge_chunks` Qdrant collection was created automatically by the backend's startup lifespan hook (`ensure_collection()`).
- Frontend responded `200` on `http://localhost:5173/` with `<title>ManifestCV</title>`, confirming `VITE_APP_NAME` reached the running container via Vite's `%VITE_APP_NAME%` substitution.
- `docker compose exec -w /repo backend pytest tests/backend` passed across mystic-auth's inherited suite plus ManifestCV's own `tests/backend/app/`.
- `docker compose exec frontend npm test` passed across mystic-auth's inherited suite plus ManifestCV's own `tests/frontend/app/`.

`docker-compose.yml` doesn't hardcode `container_name`s or the default `5432`/`6379` host ports for `postgres`/`redis` (`5433`/`6380` instead). Those are the two most common local collision points, and the stack should come up cleanly next to other local projects. Containers still reach each other at `postgres:5432`/`redis:6379`/`qdrant:6333` over the Docker network regardless of host port mappings.

### Production-readiness pass

A later audit specifically targeting `docker-compose.prod.yml` and the production build path found and fixed one release-blocking bug and several hardening gaps:

- **Production frontend build shipped `VITE_API_BASE_URL`/`VITE_APP_NAME` as `undefined`.** Confirmed by building the image both with and without the fix: without it, `localhost:8000` (the configured API base URL) appeared nowhere in the built bundle at all. With the fix (`ARG`/`ENV` in `frontend.Dockerfile`, `build.args` in `docker-compose.prod.yml`, sourced from the shell environment), the bundle's `axiosInstance` chunk correctly contains it and `<title>ManifestCV</title>` resolves correctly. This would have broken every API call and all branding in a real production deployment before the fix.
- The resume template preview originally failed in production when rendered as a direct cross-origin `<iframe>`. The current implementation fetches the PDF with axios and renders a same-origin `blob:` URL, so the inherited `X-Frame-Options: DENY` header can stay untouched. See [Document Generation](../document-generation/overview.md).
- Added rate limiting to the Gemini-triggering routes and the `tectonic` preview/finalize routes (`career_knowledge_routes.py`, `resume_routes.py`, `document_routes.py`), request-size caps on their text fields, and timeouts on both Gemini calls and `tectonic` compilation.
- Re-ran the full test suite after all of the above (`tests/backend` and `tests/frontend`, including the ManifestCV-specific suites). All passing. See [Testing Overview](../testing/overview.md).
