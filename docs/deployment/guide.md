# Deployment Guide

## Dev vs. production

| | `docker-compose.yml` | `docker-compose.prod.yml` |
|---|---|---|
| Frontend | Vite dev server (HMR) | nginx serving the static build |
| Source code | Bind-mounted from host | Baked into the image |
| Backend/worker reload | `--reload` on file change | Off |
| Restart policy | None (dev: you restart manually) | `unless-stopped` on long-running services |

Local development:

```bash
docker compose up
```

Production:

```bash
# VITE_API_BASE_URL/VITE_APP_NAME are Vite build-time vars, baked into the
# frontend bundle — they must be in the shell environment (not the root
# .env; see .env.example's note) before building, or the production
# frontend ships with both undefined.
export VITE_API_BASE_URL=https://api.example.com
export VITE_APP_NAME=ManifestCV

docker compose -f docker-compose.prod.yml up -d --build
```

`docker-compose.prod.yml` assumes a reverse proxy / TLS terminator (nginx, Caddy, Traefik, or a cloud load balancer) sits in front of it — it exposes plain HTTP on ports 80 (frontend) and 8000 (backend) and does not attempt to provision TLS itself. See [Docker Overview](../docker/overview.md).

## Required production environment variables

Same variables as `.env.example`, with these called out specifically for production:

- `ENVIRONMENT=production` — disables `/docs`, `/redoc`, and `/openapi.json` on the backend (see `backend/app/main.py`).
- `SECRET_KEY`, `GOOGLE_CLIENT_SECRET`, `GMAIL_APP_PASSWORD`, `POSTGRES_PASSWORD` — generate/rotate these for production; never reuse the values from local `.env` files or CI.
- `FRONTEND_BASE_URL` / `BACKEND_BASE_URL` — must point at the real production hostnames; CORS (`main.py`) only allows the single origin configured here.
- `TRUSTED_PROXY_IPS` — set this to your reverse proxy's own address(es) if you deploy one in front of the backend, so per-IP rate limiting/lockout resolve the real client IP from `X-Forwarded-For` instead of collapsing onto the proxy's IP for every request. Leave unset (default) for a direct deployment with no reverse proxy.
- `GEMINI_API_KEY` — required; without it the backend fails to start (`core/settings.py` has no default). Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
- `QDRANT_URL` — must point at a reachable Qdrant instance; see [Qdrant](#qdrant) below for hosting options.

## Database migrations

The `alembic` service runs `alembic upgrade head` once and exits; `backend` and `taskiq_worker` both wait on it (`depends_on: alembic: condition: service_completed_successfully` in `docker-compose.prod.yml`) so nothing serves traffic against a schema that hasn't been migrated yet.

Before applying a migration in production, review the generated migration script under `backend/alembic/versions/` — especially anything that drops or alters a column/table. Alembic's autogenerate is a starting point, not a guarantee of safety; a destructive migration should be reviewed like any other schema change before `alembic upgrade head` runs against production data.

## Backups

`scripts/db_backup.sh` and `scripts/db_restore.sh` wrap the `pg_dump`/`psql` commands below — environment-driven (read `POSTGRES_USER`/`POSTGRES_DB` from `.env`), Docker-only, no cloud/provider assumptions:

```bash
# Dump the running postgres service to backups/<db>-<timestamp>.sql
scripts/db_backup.sh
# Against the production compose file instead of the dev one:
scripts/db_backup.sh docker-compose.prod.yml

# Restore a dump (prompts for confirmation; -y skips the prompt)
scripts/db_restore.sh backups/mystic_auth-20260717-120000.sql
```

These scripts are the "how", not the "when" — there's still no scheduler wired up in this repo, since no specific production host/cloud target is assumed (see [Concerns](../concerns/README.md)). Wire `scripts/db_backup.sh` into whatever your host provides (a `cron` entry, a systemd timer, a managed Postgres provider's built-in backups, or a sidecar container), on a schedule that matches your data's change rate (daily is a reasonable default for most small apps). Store the dumps somewhere durable off the host, and periodically test a restore — an untested backup is not a backup.

Equivalent raw commands, if you'd rather not use the scripts:

```bash
docker compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup-$(date +%F).sql
docker compose exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB < backup-2026-07-13.sql
```

## Error monitoring

Optional, opt-in — `docker compose -f docker-compose.prod.yml up -d` never starts Bugsink on its own, same as the dev compose file. Bring it up alongside the rest of the production stack with:

```bash
docker compose -f docker-compose.prod.yml --profile monitoring up -d
```

`docker-compose.prod.yml` exposes no host port for `bugsink` by default (unlike `backend`/`frontend`, which are meant to be internet-facing) — reaching it in production means an SSH tunnel, a VPN, or a reverse-proxy route you add deliberately. See [Error Monitoring](../error-monitoring/overview.md) for the full setup (env vars, DSN wiring — including the internal-vs-browser DSN split that matters even more once the backend isn't on `localhost`, self-hosted Bugsink vs. Sentry's hosted tier).

## Graceful shutdown

`backend/app/main.py` registers a FastAPI `lifespan` handler that runs on shutdown (e.g. `docker stop`, or a rolling restart under an orchestrator): it disposes the SQLAlchemy connection pool and closes the Redis client cleanly instead of relying on the process dying and the OS reclaiming the sockets.

## Free / low-cost hosting options

This stack has four pieces that need hosting: backend (containerized FastAPI), frontend (static SPA build), Postgres, and Redis + a background worker process. None of the options below are endorsed as production-ready without your own evaluation of their limits (cold starts, storage caps, free-tier sleep policies) — they're a reasonable starting point for a template/side-project deployment, not a guarantee.

### Backend (FastAPI, containerized)

- **Render** (free/hobby web service tier) — deploys directly from `docker/backend.Dockerfile`; supports a separate "background worker" service type for `taskiq_worker` on the same repo. Free tier sleeps after inactivity (cold-start latency).
- **Fly.io** — deploys any Dockerfile; has a small free allowance. Good fit since the app is already fully containerized.
- **Railway** — Dockerfile-based deploys, usage-based free tier.

### Frontend (static SPA build)

- **Vercel** / **Netlify** / **Cloudflare Pages** — all have generous free tiers for a static build (`npm run build` → `frontend/dist/`); none need the `production` nginx image specifically, since they serve the static files themselves. If you do want the containerized nginx path (`docker/frontend.Dockerfile --target production`), use the same host as the backend instead.

### PostgreSQL

- **Neon**, **Supabase**, or **Railway** — all offer a free managed Postgres tier reachable over the internet; set `DATABASE_URL` to the provided connection string (must use the `postgresql+asyncpg://` scheme this app's async engine expects, not `postgresql://`).

### Redis

- **Upstash** — serverless Redis with a free tier, reachable over TLS from any host; set `REDIS_URL` accordingly. Note Upstash's free tier has request-count limits that matter here since Redis is used for rate limiting, lockout, and the taskiq broker (all high-frequency).

### Background worker (taskiq)

Needs a long-running process, not a request-driven serverless function — Render's/Railway's "background worker" service type (pointed at the same image, `command: taskiq worker app.taskiq_tasks.email_tasks:broker`) is the most direct fit among the free-tier options above.

### Qdrant

- **Self-hosted, same host as the backend** — the `qdrant/qdrant` image (see [Docker Overview](../docker/overview.md)) has no external dependencies and a small footprint; running it as a fifth container alongside `backend`/`postgres`/`redis` on the same host (Render/Fly/Railway all support multi-container or sidecar deployments) avoids a separate provider entirely.
- **Qdrant Cloud** — a managed free tier exists if self-hosting isn't an option; set `QDRANT_URL` to the provided cluster URL. Not evaluated as part of this stack's own validation (see [Docker Overview: Validation results](../docker/overview.md#validation-results)) — self-hosting alongside the backend is the tested path.

### Practical combination for a $0 deployment

Backend + worker + Qdrant on Render (three services from the same repo, two from the same image), frontend on Vercel/Netlify, Postgres on Neon, Redis on Upstash, Gemini's free tier for AI calls. Set `TRUSTED_PROXY_IPS` appropriately if the chosen backend host places its own reverse proxy in front of your container (most of the above do) — otherwise per-IP rate limiting will silently collapse onto that proxy's IP for every request.

## Limitations of this deployment approach

- No infrastructure-as-code (Terraform/Pulumi/etc.) is provided — the steps above are manual, per-provider console/CLI actions.
- No automated backups, uptime/infrastructure monitoring, or alerting are wired up anywhere in this repo — see [Concerns](../concerns/README.md). (Error tracking is available — [Error Monitoring](../error-monitoring/overview.md) above — but it's opt-in, only captures application exceptions, not infra health/uptime, and doesn't send alerts anywhere on its own; you still have to check Bugsink's Issues list, or wire its notifications up yourself.)
- Free tiers on the providers above typically have cold-start latency, storage caps, and request-volume limits not suitable for real production traffic — treat this section as a starting point for a demo/side-project deployment, not a scaling plan.
