# Docker Overview

## Services

| Service | Image / build | Purpose |
|---|---|---|
| `postgres` | `postgres:15` | Primary database |
| `redis` | `redis:7` | Cache, rate limits, lockout counters, refresh-token jti registry, single-use tokens, taskiq broker |
| `qdrant` | `qdrant/qdrant` | ManifestCV — vector store for career knowledge chunk embeddings. Self-hosted, no signup/API key/cloud account. No healthcheck: the image ships neither `curl` nor `wget` to probe its own HTTP API with, so `backend` depends on it with the default `service_started` condition rather than `service_healthy` |
| `backend` | `docker/backend.Dockerfile` | FastAPI app (uvicorn). Also bundles `tectonic` (LaTeX engine) for PDF resume compilation — see [Document Generation](../document-generation/overview.md) |
| `frontend` | `docker/frontend.Dockerfile` (`dev` target locally, `production` target in prod) | React SPA — Vite dev server locally, nginx-served static build in prod |
| `taskiq_worker` | `docker/backend.Dockerfile` (same image as `backend`, different `command:`) | Consumes the email-sending task queue — see [Background Workers](../background-workers/taskiq.md) |
| `alembic` | `docker/backend.Dockerfile` (same image, one-shot) | Runs `alembic upgrade head` then exits — applies both mystic-auth's inherited migrations and ManifestCV's own four; `backend`/`taskiq_worker` wait on its success in prod |

`backend`, `taskiq_worker`, and `alembic` all build from the **same** `docker/backend.Dockerfile` image with different `command:` overrides — keeps dependency versions and application code identical across all three roles by construction.

## Dockerfiles

- **`docker/backend.Dockerfile`** — two-stage build: a `builder` stage compiles native dependencies (`gcc`, `libpq-dev`) into an isolated venv; the runtime stage is `python:3.11-slim` with `libpq5` plus a statically-linked `tectonic` binary (fetched at build time, not full TeX Live — several GB smaller), running as a non-root `app` user. Ships a `HEALTHCHECK` against `/health/ready` as a fallback for when the image runs outside Compose.
- **`docker/frontend.Dockerfile`** — three stages: `dev` (default target — `node:20-bullseye`, Vite dev server with HMR, port 5173), `builder` (compiles the production bundle), `production` (`nginx:1.27-alpine` serving the static build as a non-root `nginx` user, port 80, `HEALTHCHECK` via `wget`). The `builder` stage takes `VITE_API_BASE_URL`/`VITE_APP_NAME` as build `ARG`s — Vite bakes them into the bundle at build time, and `frontend/.env` is deliberately excluded from the build context (`.dockerignore`), so without these args every production build would ship both as `undefined`. `docker-compose.prod.yml` passes them through as `build.args`, sourced from the shell environment (not the root `.env` — see [Deployment Guide: production](../deployment/guide.md)).
- **`docker/nginx.frontend.conf`** — SPA fallback to `index.html`, gzip, security headers. `frame-src http: https:` in its CSP specifically (rather than the `default-src 'self'` fallback) is what lets the resume template preview `<iframe>` (see [Document Generation](../document-generation/overview.md)) embed a PDF from the backend's different origin — the SPA's own CSP would otherwise block that embed independently of whatever the backend's response headers allow. No HSTS at this layer — by design, since TLS terminates in front of this container in a real deployment, not here.

## Dev vs. production compose

| | `docker-compose.yml` (dev) | `docker-compose.prod.yml` |
|---|---|---|
| Frontend | Vite dev server, HMR, bind-mounted source | nginx serving the baked-in static build |
| Backend/worker | `--reload`, bind-mounted `./backend:/app`; also mounts `./tests:/tests` alongside `frontend`'s `.:/repo`-equivalent so `docker compose exec` can run the top-level test suites | No reload, code baked into the image |
| Restart policy | `restart: always` (postgres/redis/qdrant only; backend/frontend/worker have none) | `unless-stopped` on every long-running service |
| Ports exposed | 5433 (postgres), 6380 (redis), 6333 (qdrant), 8000 (backend), 5173 (frontend) all published to host — non-default DB/cache host ports deliberately chosen to dodge the common local 5432/6379 collision; containers still reach each other at `postgres:5432`/`redis:6379`/`qdrant:6333` over the Docker network regardless | Only 8000 (backend) and 80 (frontend) published; `qdrant` uses a named volume, no host port |
| `backend`/`taskiq_worker` startup gate | `postgres`/`redis` healthy, `qdrant` started | `postgres`/`redis` healthy, `qdrant` started, **and** `alembic: service_completed_successfully` |

Both compose files assume a reverse proxy / TLS terminator sits in front of the stack in a real deployment — neither attempts to provision TLS itself. See [Deployment Guide](../deployment/guide.md).

## Test suite mounts

`backend` mounts the whole repo root additionally (`.:/repo`), and `frontend` mounts `./tests:/tests` — both let `docker compose exec` run the top-level `tests/backend/` and `tests/frontend/` suites from inside the Docker network (reaching Postgres/Redis/Qdrant via their container hostnames) without needing a host-side Python/Node environment. See [Testing Overview](../testing/overview.md#running) for the exact commands.

## Healthchecks

| Service | Check | Notes |
|---|---|---|
| `postgres` | `pg_isready` | |
| `redis` | `redis-cli ping` (with `-a` if `REDIS_PASSWORD` is set) | |
| `qdrant` | none | See Services table above |
| `backend` | `GET /health/ready` via a Python one-liner (no curl in the slim image) | Confirms DB + Redis connectivity, not just process liveness |
| `frontend` (prod) | `wget` against `/` | |
| `frontend` (dev) | none | Acceptable for local dev — Vite's own dev server failure is immediately visible in the terminal |
| `taskiq_worker` | greps `/proc/*/cmdline` for `taskiq` | Overrides the inherited HTTP healthcheck from `backend.Dockerfile`, since the worker serves no HTTP and would otherwise always report unhealthy |
| `alembic` | none | One-shot; `service_completed_successfully` is the signal other services wait on, not a healthcheck |

## Validation results

Ran `docker compose up --build` (dev compose) from the repo root after vendoring mystic-auth's latest core and wiring ManifestCV's own domains on top, and verified the merged stack end-to-end:

- All six services (`postgres`, `redis`, `qdrant`, `backend`, `taskiq_worker`, `frontend`) reached a running state; `postgres`, `redis`, `backend`, `taskiq_worker` reported `healthy` on their respective healthchecks.
- `alembic` ran the full migration chain — mystic-auth's 13 inherited migrations followed by ManifestCV's own 4 — cleanly in one pass; `\dt` against the running Postgres confirmed all inherited tables plus `career_knowledge_bases`, `resume_drafts`, `resume_documents`, `application_records`.
- `GET /` returned `{"message": "Welcome to ManifestCV!"}`; `GET /health/ready` returned `{"status":"ok","checks":{"database":"ok","redis":"ok"}}`.
- The full route inventory (`GET /openapi.json`) confirmed all four ManifestCV route groups mounted alongside every inherited mystic-auth route.
- `curl http://localhost:6333/collections` confirmed the `career_knowledge_chunks` Qdrant collection was created automatically by the backend's startup lifespan hook (`ensure_collection()`).
- Frontend responded `200` on `http://localhost:5173/` with `<title>ManifestCV</title>`, confirming `VITE_APP_NAME` reached the running container via Vite's `%VITE_APP_NAME%` substitution.
- `docker compose exec -w /repo backend pytest tests/backend` — all 599 tests passed (mystic-auth's inherited suite plus ManifestCV's own `tests/backend/manifestcv/`).
- `docker compose exec frontend npm test` — all 246 tests passed (mystic-auth's inherited suite plus ManifestCV's own `tests/frontend/manifestcv/`).

`docker-compose.yml` doesn't hardcode `container_name`s or the default `5432`/`6379` host ports for `postgres`/`redis` (`5433`/`6380` instead) — those are the two most common local collision points, and the stack should come up cleanly next to other local projects. Containers still reach each other at `postgres:5432`/`redis:6379`/`qdrant:6333` over the Docker network regardless of host port mappings.

### Production-readiness pass

A later audit specifically targeting `docker-compose.prod.yml` and the production build path found and fixed one release-blocking bug and several hardening gaps:

- **Production frontend build shipped `VITE_API_BASE_URL`/`VITE_APP_NAME` as `undefined`.** Confirmed by building the image both with and without the fix: without it, `localhost:8000` (the configured API base URL) appeared nowhere in the built bundle at all; with the fix (`ARG`/`ENV` in `frontend.Dockerfile`, `build.args` in `docker-compose.prod.yml`, sourced from the shell environment), the bundle's `axiosInstance` chunk correctly contains it and `<title>ManifestCV</title>` resolves correctly. This would have broken every API call and all branding in any real production deployment before this fix.
- **Frontend nginx CSP had no `frame-src`**, defaulting to `default-src 'self'` and silently blocking the resume template preview `<iframe>` (a different-origin embed) in production specifically — not caught by dev testing since the Vite dev server sets no CSP at all. Fixed alongside the backend-side `X-Frame-Options`/`frame-ancestors` fix for the same route (see [Document Generation](../document-generation/overview.md)).
- Added rate limiting to the Gemini-triggering routes (`career_knowledge_routes.py`, `resume_routes.py` — see each feature doc's own "Rate limiting" section), request-size caps on their text fields, and timeouts on both the Gemini calls and `tectonic` compilation (previously unbounded — a hung call would have hung the request indefinitely).
- Re-ran the full test suite after all of the above (`tests/backend` and `tests/frontend`, including the ManifestCV-specific suites) — all passing; see [Testing Overview](../testing/overview.md).
