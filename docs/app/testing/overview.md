# Testing Overview

## Backend — pytest

Config: `pytest.ini` (repo root) — `testpaths = tests/backend`, no `pythonpath` override: the suite runs from the repo root and imports modules as `backend.app.*`/`backend.mystic_auth.*`, the same dual-context convention `backend/app/sdk.py` itself uses (see [Auth & Authorization](../auth/overview.md)). `addopts = -v --cov=backend/app --cov=backend/mystic_auth --cov-report=html`. Coverage is measured and an HTML report generated (`htmlcov/`) on every invocation. **`--cov-fail-under` is deliberately not set in `pytest.ini`** — it would apply to every invocation, including partial local runs (`pytest tests/backend/mystic_auth/unit` alone covers only a slice of `backend/app`/`backend/mystic_auth` and would false-fail well under any sensible whole-project threshold). CI enforces an 80% cumulative-coverage gate once instead — see below.

| Suite | Path | Covers |
|---|---|---|
| Unit | `tests/backend/mystic_auth/unit/` (~47 files) | Auth (login/signup/logout/refresh/password reset/JWT/OAuth2/account verification), authorization (service, cache, dependency, evaluator, condition validator/schema consistency, policy routes/history/repository caching), rate limiter, login lockout, correlation ID middleware, security headers, route helpers, logging config, email tasks, user email CRUD |
| Integration | `tests/backend/mystic_auth/integration/` (8 files) | Audit log, authorization routes, auth API, health, OAuth, security audit log, security headers, user routes — real DB/Redis, real HTTP client |
| Security | `tests/backend/mystic_auth/security/` (5 files) | Batch authorization abuse, context spoofing, invalid condition payload, policy tampering, privilege escalation |
| Performance | `tests/backend/mystic_auth/performance/` (1 file) | Authorization performance |
| **ManifestCV unit** | `tests/backend/app/unit/` | `app_sdk.py` — the id-lookup helper ManifestCV routes depend on to turn mystic-auth's `get_current_user` into a DB `user_id`; the global exception handler; the knowledge-retrieval service |
| **ManifestCV integration** | `tests/backend/app/integration/` | Career knowledge, resumes, document generation, and applications routes — real DB/Redis/HTTP client, Gemini/Qdrant/tectonic mocked at each route module's import site (see each file's module docstring for why). Exception: `test_document_routes_integration.py`'s `test_real_tectonic_*` tests skip the mock and compile with the real `tectonic` binary — see [Document Generation: Testing](../document-generation/overview.md#testing) |

ManifestCV's suites live in their own subtree (`tests/backend/app/`) mirroring the upstream template's own `tests/backend/app/` (its demo consumer app's tests) — keeps "does the inherited foundation still work" and "does ManifestCV's own code work" independently runnable and independently attributable when either fails.

**Running:**

```bash
# From repo root, against local Postgres/Redis (see .env)
python -m pytest tests/backend/app/unit -q
python -m pytest tests/backend/app/integration -q
python -m pytest tests/backend/mystic_auth/unit -q
python -m pytest tests/backend/mystic_auth/integration -q
python -m pytest tests/backend/mystic_auth/security -q
python -m pytest tests/backend/mystic_auth/performance -q

# Inside the Docker network (avoids host/container Postgres port conflicts —
# see PBAC Troubleshooting)
docker compose exec -w /repo backend python -m pytest tests/backend/
```

CI (`.github/workflows/ci.yml`) runs `ruff check`, `mypy`, `bandit`, and `alembic check` first, then unit, integration, and security suites against GitHub Actions service containers (Postgres 15, Redis 7) on every push/PR to `main`. The integration and security steps pass `--cov-append` so coverage accumulates across all three suites, and the security step (running last) adds `--cov-fail-under=80` — a regression alarm against *cumulative* unit+integration+security coverage (currently ~87%), not any single suite in isolation. Performance tests also run in CI, as a **non-blocking** (`continue-on-error: true`) informational step — their thresholds are deliberately generous regression alarms rather than a strict SLA, but timing can still be noisier on shared runners than locally, hence non-blocking rather than a hard gate.

A separate `real-tectonic` CI job builds `docker/backend.Dockerfile` and runs just the `real_tectonic`-marked tests from it inside a container from that image (the only place `tectonic` is installed) — see [CI/CD Overview](../cicd/overview.md#real-tectonic--real-tectonic-pdf-compilation).

## Frontend — Vitest

Config: `frontend/vitest.config.ts` — tests physically live in `tests/frontend/` (outside `frontend/src/`) via a custom Vite resolver plugin, not co-located with source. Coverage provider `v8`, reporters `text`/`json`/`html` — same as the backend. `coverage.thresholds` (statements 85 / branches 78 / functions 79 / lines 86 — a few points below the current whole-project average of ~89/82/84/90%) are enforced, but **only when coverage is actually collected** (`vitest run --coverage`, i.e. the `test:coverage` script) — plain `vitest run` (`npm run test`) never evaluates them on its own, which is why CI runs `test:coverage` specifically (see below).

| Suite | Path | Covers |
|---|---|---|
| Unit | `tests/frontend/mystic_auth/unit/` (~33 files) | API clients (`auth`/`users`/`profile`/`policies`/`audit` endpoints, `apiError`, the refresh interceptor), `useAuthSession`, `Authorized`/`ProtectedRoute`/`Sidebar`/`Navbar`/`AppLayout` components, `useAuthorization`/`useCan`/`passwordRules`/`useUnsavedChangesWarning`, `authorizationService`, `themeStore`, `errorMonitoring`, `ui/*` (`DataTable`, `ConfirmDialog`, `FormAlert`, `PasswordRulesChecklist`, `LoadingState`, `Toaster`, `ErrorBoundary`) |
| Integration | `tests/frontend/mystic_auth/integration/` (9 files) | Audit log page, auth flow, dashboard, login page, password policy consistency, PBAC authorization flow, policies page (list, permission gating, create/edit/delete, conditions-JSON validation, unsaved-changes discard prompt), users page (list, permission gating, delete/purge/reactivate/role-change, assign/revoke via the Policies dialog), profile page (including the self-service current-password requirement) |
| **ManifestCV unit** | `tests/frontend/app/unit/api/`, `tests/frontend/app/unit/ui/` | The four ManifestCV API client modules (`application_api`, `career_knowledge_api`, `document_api`, `resume_api`) — request shape and response passthrough, mocked via `axios-mock-adapter`, same pattern as mystic-auth's own `tests/frontend/mystic_auth/unit/api/*` files; plus `Pager.tsx`, ManifestCV's own generic pagination component |
| **ManifestCV integration** | `tests/frontend/app/integration/` | App routing (including ManifestCV's own routes), `applications_page`, `career_knowledge_page`, `resume_drafts_page`, `resume_editor_page` — pagination, draft save/approve/finalize, and tracked-application-save flows. Lives in the same `tests/frontend/app/` subtree as upstream's own `app_routing.test.tsx`, mirroring `tests/backend/app/`'s split |

**Running:**

```bash
cd frontend
npm run typecheck   # three tsc --noEmit passes: app / node / test tsconfigs
npm run lint        # eslint over frontend/ and tests/frontend/
npm run test         # vitest run (no coverage collection/thresholds)
npm run test:coverage  # vitest run --coverage (thresholds enforced)

# Scope a run to just one subtree (mirrors the pytest per-suite commands above)
npx vitest run ../tests/frontend/app
npx vitest run ../tests/frontend/mystic_auth
```

CI runs `typecheck`, `lint`, `test:coverage` (not plain `test` — see above), and `build` on every push/PR to `main`.

### `.not` chaining and jest-dom/Vitest type augmentation

`frontend/tsconfig.test.json` goes to some length (see its own inline comments) to make jest-dom's Vitest matcher augmentation (`toBeInTheDocument()`, etc.) type-check via a shared module-identity `paths` mapping. That augmentation does not currently extend to chained `.not.toBe()`/`.not.toBeNull()` — `tsc` reports `Property 'not' does not exist` for those specific chains even though the same assertions type-check fine unchained. No test in this repo uses `.not.` chaining as a result; prefer a positive assertion instead (`toBeTruthy()`, an equality check phrased the other way round, etc.) — see `tests/frontend/mystic_auth/unit/layout/AppLayout.test.tsx` and `tests/frontend/mystic_auth/unit/ui/LoadingState.test.tsx` for examples.

### Slow `userEvent.type()` tests under full-suite load

A handful of integration tests type a non-trivial amount of text (a full signup form, a JSON conditions field) and then wait on an assertion — fine in isolation, but the default 5s Vitest test timeout can be too tight once the full ~55-file suite is running in parallel and CPU-contended. Rather than raising the global timeout (and hiding a real hang everywhere else), these specific tests pass an explicit longer timeout instead: `expect(await screen.findByText(..., {}, { timeout: 10000 }))` plus a `}, 15000);` third argument to `it(...)`. See `tests/frontend/mystic_auth/integration/password_policy_consistency.test.tsx` and `tests/frontend/mystic_auth/integration/policies_page.test.tsx` for the pattern — reuse it rather than reaching for the global timeout if a new test hits the same issue.

## Troubleshooting

- **A test hangs / can't connect to Postgres from the host**: a native Postgres install or another project's container on the host can still intercept whatever port is configured, even though this stack maps Postgres to the non-default host port `5433` specifically to avoid the common case. See [PBAC Troubleshooting](../../mystic_auth/authorization/troubleshooting.md#database-connection-issues) for the inherited foundation's specific failure modes.
- **Frontend test can't resolve a `tests/frontend/...` import**: confirm `frontend/vitest.config.ts`'s custom resolver plugin is active — it's what makes the split `frontend/src` / `tests/frontend` layout work; running vitest from anywhere other than `frontend/` bypasses it.
- **`docker compose exec frontend npm test` can't find any test files**: the frontend container needs `./tests/frontend:/tests/frontend` mounted (see `docker-compose.yml`'s `frontend` service).
