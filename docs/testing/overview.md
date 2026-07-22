# Testing Overview

## Backend — pytest

Config: `pytest.ini` (repo root) — `testpaths = tests/backend`, `addopts = -v --cov=backend/app --cov-report=html`. Coverage is measured and an HTML report generated (`htmlcov/`) on every invocation. **`--cov-fail-under` is deliberately not set in `pytest.ini`** — it would apply to every invocation, including partial local runs (`pytest tests/backend/unit` alone covers only a slice of `backend/app` and would false-fail well under any sensible whole-project threshold). CI enforces an 80% cumulative-coverage gate once instead — see below.

| Suite | Path | Covers |
|---|---|---|
| Unit | `tests/backend/unit/` (~45 files) | Auth (login/signup/logout/refresh/password reset/JWT/OAuth2/account verification), authorization (service, cache, dependency, evaluator, condition validator/schema consistency, policy routes/history/repository caching), rate limiter, login lockout, correlation ID middleware, security headers, route helpers, logging config, email tasks, user email CRUD |
| Integration | `tests/backend/integration/` (8 files) | Audit log, authorization routes, auth API, health, OAuth, security audit log, security headers, user routes — real DB/Redis, real HTTP client |
| Security | `tests/backend/security/` (5 files) | Batch authorization abuse, context spoofing, invalid condition payload, policy tampering, privilege escalation |
| Performance | `tests/backend/performance/` (1 file) | Authorization performance |
| **ManifestCV unit** | `tests/backend/manifestcv/unit/` | `manifestcv_sdk.py` — the id-lookup helper ManifestCV routes depend on to turn mystic-auth's `get_current_user` into a DB `user_id` |
| **ManifestCV integration** | `tests/backend/manifestcv/integration/` | Career knowledge, resumes, document generation, and applications routes — real DB/Redis/HTTP client, Gemini/Qdrant/tectonic mocked at each route module's import site (see each file's module docstring for why). Exception: `test_document_routes_integration.py`'s `test_real_tectonic_*` tests skip the mock and compile with the real `tectonic` binary — see [Document Generation: Testing](../document-generation/overview.md#testing) |

ManifestCV's suites live in their own subtree (`tests/backend/manifestcv/`) mirroring the top-level `unit`/`integration` split, rather than mixed into mystic-auth's own directories — keeps "does the inherited foundation still work" and "does ManifestCV's own code work" independently runnable and independently attributable when either fails.

**Running:**

```bash
# From repo root, against local Postgres/Redis (see .env)
python -m pytest tests/backend/unit -q
python -m pytest tests/backend/integration -q
python -m pytest tests/backend/security -q
python -m pytest tests/backend/performance -q

# Inside the Docker network (avoids host/container Postgres port conflicts —
# see PBAC Troubleshooting)
docker compose exec -w /repo backend python -m pytest tests/backend/
```

CI (`.github/workflows/ci.yml`) runs unit, integration, and security suites against GitHub Actions service containers (Postgres 15, Redis 7) on every push/PR to `main`. The integration and security steps pass `--cov-append` so coverage accumulates across all three suites, and the security step (running last) adds `--cov-fail-under=80` — a regression alarm against *cumulative* unit+integration+security coverage (currently ~87%), not any single suite in isolation. Performance tests also run in CI, as a **non-blocking** (`continue-on-error: true`) informational step — their thresholds are deliberately generous regression alarms rather than a strict SLA, but timing can still be noisier on shared runners than locally, hence non-blocking rather than a hard gate.

A separate `real-tectonic` CI job builds `docker/backend.Dockerfile` and runs just the `real_tectonic`-marked tests from it inside a container from that image (the only place `tectonic` is installed) — see [CI/CD Overview](../cicd/overview.md#real-tectonic--real-tectonic-pdf-compilation).

## Frontend — Vitest

Config: `frontend/vitest.config.ts` — tests physically live in `tests/frontend/` (outside `frontend/src/`) via a custom Vite resolver plugin, not co-located with source. Coverage provider `v8`, reporters `text`/`json`/`html` — same as the backend. `coverage.thresholds` (statements 85 / branches 78 / functions 79 / lines 86 — a few points below the current whole-project average of ~89/82/84/90%) are enforced, but **only when coverage is actually collected** (`vitest run --coverage`, i.e. the `test:coverage` script) — plain `vitest run` (`npm run test`) never evaluates them on its own, which is why CI runs `test:coverage` specifically (see below).

| Suite | Path | Covers |
|---|---|---|
| Unit | `tests/frontend/unit/` (~30 files) | API clients (`auth`/`users`/`profile`/`policies`/`audit` endpoints, `apiError`, the refresh interceptor), `useAuthSession`, `Authorized`/`ProtectedRoute`/`Sidebar`/`Navbar`/`AppLayout` components, `useAuthorization`/`useCan`/`passwordRules`/`useUnsavedChangesWarning`, `authorizationService`, `themeStore`, `errorMonitoring`, `ui/*` (`DataTable`, `ConfirmDialog`, `FormAlert`, `PasswordRulesChecklist`, `LoadingState`, `Toaster`, `ErrorBoundary`) |
| Integration | `tests/frontend/integration/` (13 files) | App routing, audit log page, auth flow, dashboard, login page, password policy consistency, PBAC authorization flow, policies page (list, permission gating, create/edit/delete, conditions-JSON validation, unsaved-changes discard prompt), users page (list, permission gating, delete/purge/reactivate/role-change, assign/revoke via the Policies dialog), profile page (including the self-service current-password requirement) — plus ManifestCV's own `applications_page`, `resume_drafts_page`, and `resume_editor_page` (pagination, draft save/approve/finalize, and tracked-application-save flows). ManifestCV's frontend integration tests are mixed into this shared directory rather than split into their own subtree the way the backend's `tests/backend/manifestcv/integration/` is — unlike the backend split (see the note above the Running section), there was no independent-attribution need strong enough to justify a parallel directory here, since these pages don't share test files with any mystic-auth-owned page |
| **ManifestCV unit** | `tests/frontend/manifestcv/unit/api/` | The four ManifestCV API client modules (`application_api`, `career_knowledge_api`, `document_api`, `resume_api`) — request shape and response passthrough, mocked via `axios-mock-adapter`, same pattern as mystic-auth's own `tests/frontend/unit/api/*` files |

**Running:**

```bash
cd frontend
npm run typecheck   # three tsc --noEmit passes: app / node / test tsconfigs
npm run lint        # eslint over frontend/ and tests/frontend/
npm run test         # vitest run (no coverage collection/thresholds)
npm run test:coverage  # vitest run --coverage (thresholds enforced)
```

CI runs `typecheck`, `lint`, `test:coverage` (not plain `test` — see above), and `build` on every push/PR to `main`.

### `.not` chaining and jest-dom/Vitest type augmentation

`frontend/tsconfig.test.json` goes to some length (see its own inline comments) to make jest-dom's Vitest matcher augmentation (`toBeInTheDocument()`, etc.) type-check via a shared module-identity `paths` mapping. That augmentation does not currently extend to chained `.not.toBe()`/`.not.toBeNull()` — `tsc` reports `Property 'not' does not exist` for those specific chains even though the same assertions type-check fine unchained. No test in this repo uses `.not.` chaining as a result; prefer a positive assertion instead (`toBeTruthy()`, an equality check phrased the other way round, etc.) — see `tests/frontend/unit/layout/AppLayout.test.tsx` and `tests/frontend/unit/ui/LoadingState.test.tsx` for examples.

## Troubleshooting

- **A test hangs / can't connect to Postgres from the host**: a native Postgres install or another project's container on the host can still intercept whatever port is configured, even though this stack maps Postgres to the non-default host port `5433` specifically to avoid the common case. See [PBAC Troubleshooting](../authorization/troubleshooting.md#database-connection-issues) for the inherited foundation's specific failure modes.
- **Frontend test can't resolve a `tests/frontend/...` import**: confirm `frontend/vitest.config.ts`'s custom resolver plugin is active — it's what makes the split `frontend/src` / `tests/frontend` layout work; running vitest from anywhere other than `frontend/` bypasses it.
- **`docker compose exec frontend npm test` can't find any test files**: the frontend container needs `./tests:/tests` mounted (see `docker-compose.yml`'s `frontend` service) so `../tests/frontend` resolves correctly relative to the container's `/app` root — this is a ManifestCV-specific addition to mystic-auth's own compose file, since mystic-auth's frontend container was never expected to run tests from inside Docker on its own.
