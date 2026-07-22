# CI/CD Overview

## Workflow

`.github/workflows/ci.yml` — triggers on every push and pull request targeting `main`. Four independent jobs, all run in parallel (no job depends on another):

### `backend` — Backend (unit + integration)

- Spins up Postgres 15 and Redis 7 as GitHub Actions **service containers** (not Docker Compose — a deliberate, lower-overhead equivalent for CI; Compose remains the source of truth for local development).
- All required settings (`SECRET_KEY`, `GOOGLE_CLIENT_ID`, `APP_NAME`, `GEMINI_API_KEY`, etc. — `core/settings.py` has no defaults for most of them) are provided as job-level env vars with clearly-fake CI-only values, since there's no checked-in `.env` for CI to read. `GEMINI_API_KEY` in particular is a placeholder only — the ManifestCV integration suite mocks every Gemini/Qdrant call at each route module's import site rather than calling either service for real, so nothing in CI ever needs a live key or a reachable Qdrant instance (no `qdrant` service container is spun up here, unlike `postgres`/`redis`).
- Installs dependencies, then runs `pip-audit -r backend/requirements.txt` (dependency vulnerability scan) before proceeding.
- Runs `alembic upgrade head` (mystic-auth's 13 inherited migrations plus ManifestCV's own 4, in one chain), then `pytest tests/backend/unit tests/backend/manifestcv/unit`, then `pytest tests/backend/integration tests/backend/manifestcv/integration --cov-append`, then `pytest tests/backend/security --cov-append --cov-fail-under=80`. The `--cov-append` flags accumulate coverage across all three steps, so the 80% gate on the final step checks *cumulative* coverage across the whole run (inherited suites + ManifestCV's own), not any one suite alone — `pytest.ini` deliberately does not bake `--cov-fail-under` into `addopts` itself, since that would also apply to (and false-fail) a developer running a single suite locally. See [Testing Overview](../testing/overview.md).
- Then runs `pytest tests/backend/performance` as a **non-blocking** (`continue-on-error: true`) step — informational only, since its thresholds, while generous regression alarms rather than a strict SLA, can still be noisier on shared GitHub-hosted runners than locally.

### `frontend` — Frontend (typecheck + lint + test + build)

- Node version is pinned to an explicit patch (`20.20.2`), not a bare major (`20`) — ESLint 10 requires Node `^20.19.0 || ^22.13.0 || >=24` and Vite 8 requires `^20.19.0 || >=22.12.0`, both above some earlier Node 20 releases, so an explicit patch guarantees the floor is met rather than trusting whichever latest-20.x a runner happens to resolve.
- `npm ci --legacy-peer-deps`, then `npm audit --audit-level=high` (dependency vulnerability scan), then `npm run typecheck`, `npm run lint`, `npm run test:coverage` (not plain `test` — coverage must actually be collected for `vitest.config.ts`'s `coverage.thresholds` to be evaluated at all), `npm run build`, each as a separate step (so the specific failing stage is visible in the Actions UI).

### `docker-build` — Docker image build verification

- Builds `docker/backend.Dockerfile` and `docker/frontend.Dockerfile --target production` to confirm both images still build cleanly.
- **No push to a registry, no deploy step** — this repo has no deploy pipeline; that's an explicit scope boundary (a template repository shouldn't assume a specific cloud/hosting target), not an oversight.

### `real-tectonic` — Real tectonic PDF compilation

- Same Postgres/Redis service containers and the same job-level env var set as `backend` above (duplicated, not shared/templated — kept simple over DRY for one job).
- Installs backend deps and runs `alembic upgrade head` directly on the runner (migrations don't need `tectonic`), then **builds `docker/backend.Dockerfile`** (the only place `tectonic` is installed — a bare `ubuntu-latest` runner doesn't have it) and runs `docker run` against that image: `pytest tests/backend/manifestcv/integration/test_document_routes_integration.py -k real_tectonic`.
- `docker run --network host` reaches the Postgres/Redis service containers via `localhost`, same as the bare-runner `backend` job; `-v "$GITHUB_WORKSPACE:/repo" -w /repo` mirrors exactly how a developer already runs this locally (`docker compose exec -w /repo backend pytest ...` — see [Docker Overview: test suite mounts](../docker/overview.md#test-suite-mounts)), not a CI-only invocation shape.
- Exists because the `backend` job's own `tests/backend/manifestcv/integration/*` mocks `render_resume_pdf` everywhere (tectonic isn't on that job's bare runner) — this job is what actually exercises the real `markdown_to_latex` → `templates` → `tectonic_compiler` pipeline in CI, catching a LaTeX-escaping or template-preamble regression that a mocked compile can't. See [Document Generation: Testing](../document-generation/overview.md#testing).

## What's covered

- Backend unit/integration/security suites, against real Postgres/Redis, gated by an 80% cumulative-coverage threshold (actual coverage runs a few points above this — see [Testing Overview](../testing/overview.md)); performance tests run too, non-blocking.
- Full frontend type-check, lint, test (with coverage thresholds enforced), and production build.
- Both Docker images still build.
- Real `tectonic` PDF compilation, inside the actual production backend image — not just mocked.
- Dependency vulnerability scanning on every push/PR: `pip-audit` (backend) and `npm audit --audit-level=high` (frontend) — lightweight steps added to the existing jobs, not new jobs, so CI time is barely affected. There is no scheduled/automated dependency-update bot in this repo — dependency bumps are a manual, deliberate action (see the header comment in `backend/requirements.txt`), not something that opens PRs on its own.

## What's not covered (tracked, not silently missing)

See [Concerns](../concerns/README.md) for the full entries:

- No image push to a registry and no deployment stage — deploying is a manual, documented process (see [Deployment Guide](../deployment/guide.md)), not automated.

This is deliberately left as a documented gap rather than added — extending `ci.yml` with a deploy stage is a workflow change with its own blast radius (new required checks, new secrets, a specific hosting target to assume), and unnecessary cloud-specific tooling doesn't belong in a template repository with no assumed production target.

## Local equivalents

Everything CI runs can be run locally:

```bash
# Backend (from repo root, against local or Dockerized Postgres/Redis)
python -m pytest tests/backend/unit tests/backend/manifestcv/unit tests/backend/integration tests/backend/manifestcv/integration tests/backend/security -q
python -m pytest tests/backend/performance -q

# Frontend (from frontend/)
npm run typecheck && npm run lint && npm run test:coverage && npm run build

# Docker image builds (from repo root)
docker build -f docker/backend.Dockerfile -t backend:local .
docker build --target production -f docker/frontend.Dockerfile -t frontend:local .

# Real-tectonic tests (needs the built backend image — see docker-compose.yml's
# dev backend service, which already has tectonic installed)
docker compose exec -w /repo backend pytest tests/backend/manifestcv/integration/test_document_routes_integration.py -k real_tectonic -v
```
