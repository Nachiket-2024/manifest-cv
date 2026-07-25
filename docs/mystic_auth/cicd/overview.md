# CI/CD Overview

## Workflow

`.github/workflows/ci.yml` — triggers on every push and pull request targeting `main`. Declares top-level `permissions: contents: read` — none of the jobs below push commits, comment on PRs, or need any write access, so the default `GITHUB_TOKEN` is scoped down explicitly rather than left at whatever the repo/org default happens to be; a compromised action dependency in this workflow can't do more than read the checkout. Four independent jobs, all run in parallel (no job depends on another):

```mermaid
flowchart LR
    Trigger(["Push / PR to main"])

    Trigger --> Backend["backend<br/><small>lint, type-check, bandit,<br/>pip-audit, pytest (85% cov gate)</small>"]
    Trigger --> Frontend["frontend<br/><small>typecheck, lint,<br/>test:coverage, build</small>"]
    Trigger --> Secrets["secrets-scan<br/><small>gitleaks, full git history</small>"]
    Trigger --> DockerBuild["docker-build<br/><small>build both images,<br/>assert no leaked logs</small>"]
```

### `backend` — Backend (unit + integration)

- Spins up Postgres 15 and Redis 7 as GitHub Actions **service containers** (not Docker Compose — a deliberate, lower-overhead equivalent for CI; Compose remains the source of truth for local development).
- All required settings (`SECRET_KEY`, `GOOGLE_CLIENT_ID`, `APP_NAME`, etc. — `core/settings.py` has no defaults for most of them) are provided as job-level env vars with clearly-fake CI-only values, since there's no checked-in `.env` for CI to read. `APP_NAME` in particular is set to `MysticAuth` here purely because `Settings` requires *some* value and refuses to start without one — it has no bearing on the actual product name. If you've cloned this repo as a template and renamed the app (see [Using This Repository as a Template: renaming the app](../template-usage.md#renaming-the-app)), there's no need to touch this CI value to match — it's a placeholder for test runs, not branding that needs to stay in sync with your `.env`.
- Installs both `backend/requirements.txt` and `backend/requirements-dev.txt` (ruff, mypy, bandit — static-analysis-only, never installed in the runtime image), then runs `pip-audit -r backend/requirements.txt` (dependency vulnerability scan) before proceeding.
- Runs `ruff check`, `mypy`, and `bandit -c pyproject.toml` (all three configured in `backend/pyproject.toml`) — lint, type-check, and a Python-specific security scan, each as its own step so the specific failing tool is visible in the Actions UI.
- Runs `alembic upgrade head`, then `alembic check` — the latter fails if any SQLAlchemy model's columns/indexes have drifted from what the migrations actually create (e.g. a model field changed without a matching migration).
- Then `pytest tests/backend/app tests/backend/mystic_auth/unit` (the thin `app/` wrapper's own tests run alongside the `mystic_auth/` unit suite, as one coverage base), then `pytest tests/backend/mystic_auth/integration --cov-append`, then `pytest tests/backend/mystic_auth/security --cov-append --cov-fail-under=85`. The `--cov-append` flags accumulate coverage across all three steps, so the 85% gate on the final step checks *cumulative* unit+integration+security coverage (currently ~89%), not any one suite alone — `pytest.ini` deliberately does not bake `--cov-fail-under` into `addopts` itself, since that would also apply to (and false-fail) a developer running a single suite locally. See [Testing Overview](../testing/overview.md).
- Then runs `pytest tests/backend/mystic_auth/performance` as a **non-blocking** (`continue-on-error: true`) step — informational only, since its thresholds, while generous regression alarms rather than a strict SLA, can still be noisier on shared GitHub-hosted runners than locally.

### `frontend` — Frontend (typecheck + lint + test + build)

- Node version is pinned to an explicit patch (`20.20.2`), not a bare major (`20`) — ESLint 10 requires Node `^20.19.0 || ^22.13.0 || >=24` and Vite 8 requires `^20.19.0 || >=22.12.0`, both above some earlier Node 20 releases, so an explicit patch guarantees the floor is met rather than trusting whichever latest-20.x a runner happens to resolve.
- `npm ci --legacy-peer-deps`, then `npm audit --audit-level=high` (dependency vulnerability scan), then `npm run typecheck`, `npm run lint`, `npm run test:coverage` (not plain `test` — coverage must actually be collected for `vitest.config.ts`'s `coverage.thresholds` to be evaluated at all), `npm run build`, each as a separate step (so the specific failing stage is visible in the Actions UI).

### `secrets-scan` — Secrets scan (gitleaks)

- Checks out full git history (`fetch-depth: 0`, not just the latest commit) and runs [gitleaks](https://github.com/gitleaks/gitleaks) against it — catches a secret that was committed and later "removed" (but still sits in history), not just what's in the current working tree.

### `docker-build` — Docker image build verification

- Builds `docker/backend.Dockerfile` and `docker/frontend.Dockerfile --target production` to confirm both images still build cleanly.
- Then runs the built backend image and asserts `/app/logs` does **not** exist inside it — a regression guard for a real bug found during a production-readiness review (local access-log files, with real request data, were previously getting baked into the image via a `.dockerignore` gap — see [Security Decisions](../security/decisions.md#dockerignore-previously-let-local-files-leak-into-built-images)). This is the one place in `docker-build` that checks image *contents*, not just that the build succeeds.
- **No push to a registry, no deploy step** — this repo has no deploy pipeline; that's an explicit scope boundary (a template repository shouldn't assume a specific cloud/hosting target), not an oversight.

## What's covered

- Backend unit/integration/security suites, against real Postgres/Redis, gated by an 85% cumulative-coverage threshold; performance tests run too, non-blocking.
- Backend lint (ruff), type-checking (mypy), and security scanning (bandit) — all configured in `backend/pyproject.toml`.
- A model/migration drift check (`alembic check`) — fails if a SQLAlchemy model's columns or indexes don't match what the checked-in migrations actually produce.
- Full frontend type-check, lint, test (with coverage thresholds enforced), and production build.
- Both Docker images still build.
- Dependency vulnerability scanning on every push/PR: `pip-audit` (backend) and `npm audit --audit-level=high` (frontend). There is no scheduled/automated dependency-update bot in this repo — dependency bumps are a manual, deliberate action (see the header comment in `backend/requirements.txt`), not something that opens PRs on its own.
- Secret scanning across full git history (`gitleaks`), independent of the backend/frontend jobs.

## What's not covered (tracked, not silently missing)

See [Concerns](../concerns/README.md) for the full entries:

- No image push to a registry and no deployment stage — deploying is a manual, documented process (see [Deployment Guide](../deployment/guide.md)), not automated.

This is deliberately left as a documented gap rather than added — extending `ci.yml` with a deploy stage is a workflow change with its own blast radius (new required checks, new secrets, a specific hosting target to assume), and unnecessary cloud-specific tooling doesn't belong in a template repository with no assumed production target.

## Local equivalents

Everything CI runs can be run locally:

```bash
# Backend static analysis (from repo root; dev tools installed via requirements-dev.txt)
# ruff's import-sorting/per-file-ignore rules are path-relative to its own
# working directory, not to --config's location, so this one still needs a
# `cd` — kept a single self-contained line so it doesn't change your shell's
# directory afterward.
(cd backend && ruff check app mystic_auth alembic ../tests/backend)
mypy --config-file backend/pyproject.toml backend/app backend/mystic_auth
bandit -r backend/app backend/mystic_auth -c backend/pyproject.toml
alembic -c backend/alembic.ini check

# Backend tests (from repo root, against local or Dockerized Postgres/Redis)
python -m pytest tests/backend/app tests/backend/mystic_auth/unit tests/backend/mystic_auth/integration tests/backend/mystic_auth/security -q
python -m pytest tests/backend/mystic_auth/performance -q

# Frontend (from repo root)
npm run typecheck --prefix frontend && npm run lint --prefix frontend && npm run test:coverage --prefix frontend && npm run build --prefix frontend

# Secrets scan (from repo root; requires gitleaks installed, or run via Docker)
gitleaks detect --source . -v

# Docker image builds (from repo root)
docker build -f docker/backend.Dockerfile -t backend:local .
docker build --target production -f docker/frontend.Dockerfile -t frontend:local .
```
