# Using This Repository as a Template

You've cloned this repo to build your own product's authentication and authorization layer on top of it. This doc is the "never seen this codebase before" starting point — what you get, how to stand it up, and where to make it yours. Every other doc in [`docs/`](README.md) describes *how the system works*; this one is about *what to do with it*.

## What this template provides

- **Authentication**: email+password signup with Argon2 hashing, email verification, login with dual rate limiting and brute-force lockout, Google OAuth2 with PKCE, JWT access+refresh tokens delivered as httpOnly cookies, refresh-token rotation with reuse detection, logout / logout-all, and a full forgot-password → reset-password flow. See [Authentication Overview](authentication/overview.md).
- **Authorization**: Policy-Based Access Control (PBAC), not RBAC. Every protected route is gated by an assigned, active `Policy` — not by a user's `role`. Policies are data (rows in Postgres), not code, so a new access pattern is a new policy, not a new deploy. See [PBAC Architecture](authorization/architecture.md) and [Security Decisions: role is never used to decide access](security/decisions.md#role-is-never-used-to-decide-access).
- **Audit logging**: two independent, append-only audit tables — a security/session-event log (login, logout, signup, lockout, account lifecycle) and a PBAC decision log (every `allow`/`deny` authorization check, with the policies that were evaluated). See [Database Design: why two audit tables](database/design.md#why-two-audit-tables-not-one).
- **Frontend**: React 19 + TypeScript SPA built with Vite, Chakra UI v3 for components/theming, Zustand for client/session state, TanStack Query for server-state caching. Feature-organized to mirror the backend's domain split. See [Frontend Architecture](architecture/frontend.md).
- **Infrastructure**: Docker Compose for local dev and production, PostgreSQL, Redis (caching/rate-limiting/token registry/Taskiq broker), Taskiq for async email delivery, Alembic for migrations, and a GitHub Actions CI workflow.
- **Error monitoring**: optional, disabled by default. Backend (`sentry-sdk[fastapi]`) and frontend (`@sentry/react`) reporting via the Sentry SDK protocol, with a self-hosted Bugsink quickstart documented — set `SENTRY_DSN`/`VITE_SENTRY_DSN` to turn it on. See [Error Monitoring](error-monitoring/overview.md).

> **This document describes the upstream [mystic-auth](https://github.com/Nachiket-2024/mystic-auth) template as-is** — including its default layout, where the template's own code lives directly under `backend/app/`/`frontend/src/` rather than in a separate package. **ManifestCV (this repository) is a real, deployed consumer of it, and additionally keeps the vendored template physically separate from its own code** — mystic-auth lives in `backend/mystic_auth/`/`frontend/src/mystic_auth/`, ManifestCV's own feature modules (`application_*`/`resume_*`/`career_knowledge_*`, etc.) in `backend/app/`/`frontend/src/` — see [ManifestCV's own `docs/README.md`](README.md) and [Auth & Authorization](auth/overview.md) for how that split works and how it's kept mechanical. Keeping this file byte-for-byte close to upstream (rather than rewriting it for ManifestCV specifically) is deliberate, so the [Staying in sync with upstream template updates](#staying-in-sync-with-upstream-template-updates) section below stays accurate for anyone comparing the two.

## Quickstart

```bash
git clone https://github.com/Nachiket-2024/mystic-auth.git
cd mystic-auth
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Fill in `.env` and `frontend/.env` — at minimum `SECRET_KEY` (32+ characters, the app refuses to start otherwise), `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`, and `APP_NAME`/`VITE_APP_NAME` if you want your own product name from the start. Google OAuth2 and email vars can be filled in later (see below) — the app runs without them, but signup/login via those specific paths won't work until they're set.

```bash
docker compose up
```

Once the stack is up:

- **Backend**: [http://localhost:8000/docs](http://localhost:8000/docs) — FastAPI interactive docs
- **Frontend**: [http://localhost:5173](http://localhost:5173) — Vite dev server
- **PostgreSQL**: `localhost:5433` (host-side; containers reach it at `postgres:5432` internally — the non-default host port dodges the common local-Postgres collision, see [Docker Overview](docker/overview.md))
- **Redis**: `localhost:6380` (host-side; containers reach it at `redis:6379` internally, same reasoning)

`docker compose up` deliberately does **not** start the optional self-hosted Bugsink error-monitoring service — it's a separate opt-in profile (`docker compose --profile monitoring up -d`), so it won't appear even after the command above finishes. See [Error Monitoring](error-monitoring/overview.md) if you want it.

Then create the reserved system superuser (one-time, CLI-only — it can never be created or promoted via any API route):

```bash
docker compose exec -it backend python -m app.scripts.create_system_user
```

> **In this repo specifically** (ManifestCV, where `scripts/` moved to `backend/mystic_auth/scripts/` — see [Auth & Authorization](auth/overview.md)), the module path is `mystic_auth.scripts.create_system_user`, not `app.scripts.create_system_user`. Root [`README.md`](../README.md#-first-time-setup--creating-the-system-superuser) always has the exact, current command for this repo; the command above is what a fresh, standalone clone of the upstream template uses.

See root [`README.md`](../README.md) for the interactive prompts, and [Policy JSON Examples: system superuser policy](authorization/policy-examples.md#system-superuser-policy-seeded) for what that account can do out of the box.

## Environment configuration

Full variable-by-variable reference lives in [`.env.example`](../.env.example) (backend) and `frontend/.env.example` (frontend) — every setting is documented inline there with a one-line comment, grouped by category (database, JWT/tokens, OAuth2, Redis, email, login protection, rate limiting, logging, environment, reverse proxy, error monitoring, and — in this repo specifically — ManifestCV's own Gemini/Qdrant settings). Copy each to its real `.env` and treat those `.example` files as the source of truth, not this doc.

> **In this repo specifically**, there is no separate `frontend/.env.example` — every `VITE_*` var lives in the same root [`.env.example`](../.env.example) as the backend settings, and `frontend/vite.config.ts`'s `envDir: '..'` is what points the dev server (and the production build's `docker-compose.prod.yml`) at that one file instead of a `frontend/`-local one. The two-file layout below is the standalone template's own default.

One pair is worth calling out specifically, since it's the main "make this yours" hook:

| Variable | File | Purpose |
|---|---|---|
| `APP_NAME` | `.env` | Product name used in email templates and the root `/` API response. Required — no fallback. |
| `VITE_APP_NAME` | `frontend/.env` (`.env` in this repo — see above) | Product name shown in the UI (navbar, auth pages) and the browser tab title (`frontend/index.html`'s `%VITE_APP_NAME%` substitution, resolved by Vite at build time). |

## Renaming the app

Change `APP_NAME` and `VITE_APP_NAME` in `.env` (`frontend/.env` in a standalone template clone — see above), then restart (`docker compose up --build` if the frontend image was already built, since `VITE_APP_NAME` is baked in at build time, not read at runtime). Nothing else in the codebase hardcodes a product name — there's no other file to touch.

**CI still uses `APP_NAME=ManifestCV`, and that's fine.** `.github/workflows/ci.yml` sets `APP_NAME` (and every other required setting) directly as a job-level environment variable, since there's no checked-in `.env` for CI to read — `Settings` refuses to start without a value for it, so CI needs *something*. That value is a placeholder for test runs, not branding — see [CI/CD Overview](cicd/overview.md).

## Frontend customization

- **Design tokens / theme**: `frontend/src/theme/system.ts` — Chakra UI v3 tokens (colors, semantic tokens for brand/surface/border/text). Change the `brand` color scale here to re-skin the whole app; components reference tokens (`colorPalette="brand"`, `bg="bg.surface"`, etc.), not raw hex values.
- **Pages/features**: `frontend/src/` is organized by feature, one folder per domain — `auth/` (login, signup, logout, oauth2, password reset, account verification), `dashboard/`, `profile/`, `users/`, `policies/`, `audit_log/`, plus ManifestCV's own `career_knowledge/`, `resumes/`, `applications/`. Each auth sub-feature is its own folder with its Page/Form/mutation-hook/types together. Import `PERMISSIONS`, `useAuthorization`, `ProtectedRoute`, `api`, etc. from `frontend/src/sdk.ts` (above), not from their internal locations. See [Frontend Architecture: module layout](architecture/frontend.md#module-layout) for the full table.
- **Routing**: all routes are declared in `frontend/src/App.tsx` — add a new `<Route>` there, wrapped in `ProtectedRoute` (optionally with a `permission` prop, see [Frontend Architecture: routing](architecture/frontend.md#routing)) and `AppLayout` if it needs the sidebar/top-bar shell.
- **State**: `frontend/src/store/` — Zustand for client state (`authStore`, `themeStore`). `frontend/src/core/queryClient.ts` holds the shared TanStack Query client. `frontend/src/api/` holds Axios-based typed call functions per backend domain. `authStore` and `queryClient` are re-exported from `frontend/src/sdk.ts`.

## The extension surface: `sdk.py` / `sdk.ts`

`backend/app/sdk.py` and `frontend/src/sdk.ts` are the intended door into this template for your own domain/feature code — a single file on each side that re-exports the pieces you're meant to build on (`require_authorization`, `Permission`, `useAuthorization`, `ProtectedRoute`, the shared `api` client, `capture_exception`/`reportError` for [error monitoring](error-monitoring/overview.md), and so on). Your own code imports from `app.sdk` / `@/sdk`, not by reaching into internal paths like `app.authorization.dependencies.authorization_dependency` or `frontend/src/authorization/useAuthorization` directly.

This isn't a published package — it's just two plain files, each with a docstring at the top listing everything it re-exports and why. Two things it buys you over importing internals directly everywhere:

1. **One place to read**, instead of hunting through the template's internals for "what am I actually supposed to import here."
2. **One place a merge conflict can land**, instead of many. If a future upstream update moves or renames something internal (this template's own frontend went through exactly that reorganization recently — see [Frontend Architecture](architecture/frontend.md)), only `sdk.py`/`sdk.ts` need reconciling to match the new internal path. Your own domain code underneath it, which only ever imported from the SDK file, doesn't need to change at all. See [Staying in sync with upstream template updates](#staying-in-sync-with-upstream-template-updates) below for why that matters.

It's deliberately *not* a full abstraction layer — it doesn't wrap or hide the underlying APIs, it just re-exports them under one stable, greppable path. You're still reading the real docs (PBAC Architecture, Authentication Overview, Frontend Architecture) to understand what each piece actually does; the SDK file only changes *where you import it from*.

ManifestCV additionally has its own `backend/app/manifestcv_sdk.py` — the counterpart to `app.sdk`, but for glue ManifestCV's own route modules need that the upstream template has no reason to provide (currently just `get_user_id_by_email`, since mystic-auth's `get_current_user` returns email/role/permissions, never a database `id`, and ManifestCV's own feature tables use `user_id` as their foreign key). This file is not part of the upstream template and is never reconciled against an upstream update — see that file's own docstring.

## Backend customization

> Every `backend/app/`-prefixed path and `app.sdk` import in this section describes a **fresh, standalone clone of the template** — i.e. what you'd see if you started from mystic-auth directly. In **this repo** (ManifestCV), the template itself lives at `backend/mystic_auth/` instead, so read `backend/app/sdk.py` as `backend/mystic_auth/sdk.py`, `from app.sdk import ...` as `from mystic_auth.sdk import ...`, and so on throughout this page — see [Auth & Authorization](auth/overview.md) for the exact mapping and why the split exists. `backend/app/manifestcv_sdk.py` mentioned just above is the one exception: it's ManifestCV's own file and really does live at that exact path in this repo too.

- **Adding your own domain/resource** (e.g. `projects`, `documents`): follow the existing module pattern — a new top-level package under `backend/app/` with its own `*_model.py`, `*_schema.py`, `*_crud*.py`, and a router under `backend/app/api/` mounted in `backend/app/main.py`. Import `require_authorization`, `Permission`, `get_current_user`, `database`, `settings`, etc. from `backend/app/sdk.py` (above), not from their internal locations. See [Backend Architecture: module layout](architecture/backend.md#module-layout) for how the existing modules (`auth/`, `user_table/`, `user_crud/`) are shaped — and ManifestCV's own `career_knowledge_*`/`resume_*`/`application_*`/`document_*` modules for a real worked example of this pattern applied end-to-end.
- **Database changes**: every schema change is an Alembic migration under `backend/alembic/versions/` — no `create_all()` anywhere. See [Database Design](database/design.md#migrations).
- **Configuration**: all settings are centralized in `backend/app/core/settings.py` (`pydantic-settings`, env-driven) — add new settings there, never read `os.environ` directly elsewhere. Re-exported from `backend/app/sdk.py` as `settings`.

## PBAC usage

### Adding a new permission

Business-domain actions (e.g. `"projects:create"`, `"documents:view"`) don't need to go in the `Permission` enum at all — a policy can grant any action string freely. Only add an enum member in `backend/app/authorization/permissions.py` if the action is sensitive enough that you want the privilege-escalation guard applied (see [Adding New Permissions](authorization/adding-permissions.md) for the full guidance, including how to update seed policies via a data-only migration).

### Protecting a new route

Every protected route depends on `require_authorization(action, resource_type)` — never a role check. A real, worked example, adapted from `user_routes.py` (`backend/app/api/user_routes/` in a standalone template clone; `backend/mystic_auth/api/user_routes/` in this repo) to import from the SDK surface (above) the way your own new route module should — swap `app.sdk` for `mystic_auth.sdk` if you're following this repo's own layout rather than a fresh template clone:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.sdk import require_authorization, Permission, database

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/")
async def list_all_projects(
    current_user: dict = Depends(require_authorization("projects:list_all", "projects")),
    db: AsyncSession = Depends(database.get_session)
):
    return await project_crud.get_all(db)
```

`require_authorization(action, resource_type)` is a dependency factory (`backend/app/authorization/dependencies/authorization_dependency.py`, re-exported from `app.sdk`) that builds the request's authorization context and calls `AuthorizationService.require(...)` for you — raising `403` if no assigned, active policy grants that action on that resource type (optionally condition-gated by time, network, ownership, etc.). For your own resources, `resource_type` doesn't need to be a `Permission` enum value at all — pass any string you want (`"projects"`, `"documents"`) and grant the matching action string via a policy (see [Writing and Testing Policies](authorization/writing-testing-policies.md#policy-creation-workflow)).

ManifestCV's own routes take a slightly different, deliberate shape for their own resources (career knowledge, resume drafts, applications): no PBAC permission is required at all, since every one of those resources is strictly self-service (a caller can only ever see/edit their own rows, enforced by `user_id`-scoped queries built from `get_current_user`'s email via `manifestcv_sdk.get_user_id_by_email`, never a caller-supplied id) — see each route module's own top-of-file comment for why PBAC wasn't the right fit there specifically.

If the route needs to check a *different* action depending on runtime data (like `user_routes.py`'s role-assignment route does — assigning `system` role needs a stricter action than assigning any other role), call `authorization_service.require(...)` directly inside the handler instead of relying solely on the route-level dependency; see that route's own code for the pattern.

## Replacing the frontend entirely

The backend has no frontend-specific coupling — it's a stateless JSON API you can drive from any client. What it expects:

- **Cookie-based JWT auth**: `access_token` (path `/`) and `refresh_token` (path `/auth`, scoped), both httpOnly/secure/`SameSite=Strict`. There is no bearer-token/header auth mode — a replacement client must send/receive cookies (`withCredentials`/`credentials: "include"` equivalent) and be served from an origin matching `FRONTEND_BASE_URL` (CORS only allows that one origin).
- **The full route contract** (paths, methods, auth requirements, request/response shapes): [API Reference](api/reference.md).

Nothing in the backend imports from or references `frontend/` — deleting the entire `frontend/` directory and building a new client (a different SPA, a mobile app, a server-rendered app) against the same API is a supported use of this template.

## OAuth setup (Google)

Mechanics (PKCE, CSRF `state`, account-hijack handling) are covered in [OAuth2 / PKCE](authentication/oauth2-pkce.md). To get it working for your own Google Cloud project:

1. Create an OAuth 2.0 Client ID in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) (Web application type).
2. Add an authorized redirect URI that exactly matches `GOOGLE_REDIRECT_URI` below (scheme, host, path, and trailing slash all matter — a mismatch is the most common setup failure, see [OAuth2 / PKCE: troubleshooting](authentication/oauth2-pkce.md#troubleshooting)).
3. Fill in `.env`:

   | Variable | Value |
   |---|---|
   | `GOOGLE_CLIENT_ID` | From the Cloud Console credential |
   | `GOOGLE_CLIENT_SECRET` | From the Cloud Console credential |
   | `GOOGLE_REDIRECT_URI` | Must match the Console-registered URI exactly, e.g. `http://localhost:8000/auth/oauth2/callback/google` for local dev |

## Email setup

Mechanics (Taskiq broker, HTML templates, failure handling) are covered in [Background Workers: Taskiq](background-workers/taskiq.md). To send real email:

| Variable | Purpose |
|---|---|
| `FROM_EMAIL` | The Gmail account sending mail (also the SMTP auth username) |
| `GMAIL_APP_PASSWORD` | A Gmail [App Password](https://myaccount.google.com/apppasswords) (not your normal account password — requires 2FA enabled on the Google account) |
| `SUPPORT_EMAIL` | Optional; used as the `Reply-To` header, falls back to `FROM_EMAIL` if unset |

Without valid values here, signup/verification/password-reset emails will fail to send — `send_email_task` logs the full traceback and retries up to 3 times (see [Background Workers: Taskiq](background-workers/taskiq.md)) — but the rest of the app keeps working.

## Deployment

Covered in full in ManifestCV's own [Deployment Guide](deployment/guide.md) — dev vs. production Compose topology, required production environment variables (including ManifestCV's own `GEMINI_API_KEY`/`QDRANT_URL`), database migrations, backup runbook, and free/low-cost hosting options for each piece of the stack. Production Compose file: [`docker-compose.prod.yml`](../docker-compose.prod.yml).

## Staying in sync with upstream template updates

You cloned this repo at a point in time. This template keeps changing after that — bug fixes (like a real one: logout used to fail right after a password change, since that change revokes the session's own refresh token — fixed in `backend/app/auth/logout/logout_handler.py`, see [Security Decisions](security/decisions.md)), new docs, small architectural cleanups. This section is how to keep pulling those in without it turning into a mess, explained from scratch — none of this assumes you already know git remotes.

### What a "remote" is, and why you'll want two

When you `git clone` a repository, git records where you cloned it from as a **remote** named `origin` by convention. Every `git push`/`git pull` you've run so far talked to `origin` — which, if you followed the normal fork-and-clone flow, is *your own* copy (e.g. your own GitHub fork), not this original template repo.

A remote is nothing more than "a name git has for some other repository's URL, so you can type the name instead of the URL every time." You're not limited to one. Add a second remote pointing at the *original* template repo, conventionally named `upstream`:

```bash
git remote add upstream https://github.com/Nachiket-2024/mystic-auth.git
```

Check it worked:

```bash
git remote -v
# origin    <your fork's URL> (fetch)
# origin    <your fork's URL> (push)
# upstream  https://github.com/Nachiket-2024/mystic-auth.git (fetch)
# upstream  https://github.com/Nachiket-2024/mystic-auth.git (push)
```

You only need to do this once, ever, per local clone.

### Pulling in updates

```bash
git fetch upstream
```

`fetch` downloads upstream's commits into your local git history *without touching your working files yet* — it's the safe, look-before-you-leap step. Before merging anything, see what actually changed:

```bash
git log HEAD..upstream/main --oneline
```

(`main` here is upstream's default branch — check `git remote show upstream` if you're unsure it's still called that.) When you're ready to actually bring those commits into your own branch:

```bash
git merge upstream/main
```

This is a normal git merge — same mechanics as merging any other branch. If your own changes and upstream's changes touched different files (the common case, if you've been extending via new files as this doc recommends), it merges cleanly with no extra steps. If both sides touched the same lines of the same file, git stops and asks you to resolve the conflict by hand, same as any merge conflict.

### What's likely to conflict, and what almost never will

- **Your own new top-level packages/feature folders** (`backend/app/projects/`, `frontend/src/projects/` — or, in this repo, `career_knowledge_*`/`resume_*`/`application_*`/`document_*`) — upstream has no idea they exist and will never touch them. These should essentially never conflict.
- **`backend/app/sdk.py` / `frontend/src/sdk.ts`** — the one place expected to occasionally conflict, and by design: if upstream moves or renames something internal (see [The extension surface](#the-extension-surface-sdkpy--sdkts) above), the conflict is contained to these two files instead of scattered across every place your own code imported the old internal path directly. Resolving it here is a normal, expected part of syncing — not a sign something went wrong.
- **Files you customized directly instead of extending** — if you added your own settings fields into the middle of `backend/app/core/settings.py`, or edited `backend/app/main.py`'s router registration in place, or hand-edited `frontend/src/App.tsx`'s route list, those are exactly the files upstream is also most likely to touch over time. This is the tradeoff for customizing in place rather than through the SDK/extension points above — it's not wrong, it's just where you should expect to spend conflict-resolution time. ManifestCV's own additions to exactly these files (`settings.py`'s Gemini/Qdrant block, `main.py`'s extra routers, `App.tsx`'s extra routes) are all kept in clearly-commented, additive blocks for exactly this reason.
- **Docs you've personalized** (README, this file) — expected to conflict if you've edited them; resolve however you'd resolve any other doc conflict (usually: keep your version, since these describe your product now, not the template).

### After merging

Rebuild and re-run the full test suite before trusting the merge — a merge can silently change behavior underneath you even when git resolved every conflict automatically:

```bash
docker compose up -d --build
docker compose exec -w /repo backend python -m pytest tests/backend/unit tests/backend/integration tests/backend/security
# frontend: see docs/testing/overview.md for the equivalent typecheck/lint/test/build commands
```

## Where to go next

- New to the codebase generally? Start at [`docs/README.md`](README.md) for the full documentation index.
- Building your first protected feature? [Adding New Permissions](authorization/adding-permissions.md) → protect the route (above) → [Writing and Testing Policies](authorization/writing-testing-policies.md) to create and assign the policy that grants it.
- Something not behaving as documented? [PBAC Troubleshooting](authorization/troubleshooting.md) covers the most common authorization/Docker/Redis issues.

## Getting help

Stuck on something this doc set doesn't answer for the underlying template? Search [existing mystic-auth GitHub Issues](https://github.com/Nachiket-2024/mystic-auth/issues) first, then open a new one there with clear reproduction steps if it's about the inherited foundation rather than ManifestCV's own feature code.

**Found a security vulnerability?** Don't open a public Issue for it — see mystic-auth's [SECURITY.md](https://github.com/Nachiket-2024/mystic-auth/blob/main/SECURITY.md) for how to report it privately.
