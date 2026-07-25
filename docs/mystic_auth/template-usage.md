# Using This Repository as a Template

You've created your own repository from this template (via GitHub's **Use this template** button) to build your own product's authentication and authorization layer on top of it. This doc is the "never seen this codebase before" starting point — what you get, how to stand it up, and where to make it yours. Every other doc in [`docs/`](README.md) describes *how the system works*; this one is about *what to do with it*.

## What this template provides

- **Authentication**: email+password signup with Argon2 hashing, email verification, login with dual rate limiting and brute-force lockout, Google OAuth2 with PKCE, JWT access+refresh tokens delivered as httpOnly cookies, refresh-token rotation with reuse detection, logout / logout-all, and a full forgot-password → reset-password flow. See [Authentication Overview](authentication/overview.md).
- **Authorization**: Policy-Based Access Control (PBAC), not RBAC. Every protected route is gated by an assigned, active `Policy` — not by a user's `role`. Policies are data (rows in Postgres), not code, so a new access pattern is a new policy, not a new deploy. See [PBAC Architecture](authorization/architecture.md) and [Security Decisions: role is never used to decide access](security/decisions.md#role-is-never-used-to-decide-access).
- **Audit logging**: two independent, append-only audit tables — a security/session-event log (login, logout, signup, lockout, account lifecycle) and a PBAC decision log (every `allow`/`deny` authorization check, with the policies that were evaluated). See [Database Design: why two audit tables](database/design.md#why-two-audit-tables-not-one).
- **Frontend**: React 19 + TypeScript SPA built with Vite, Chakra UI v3 for components/theming, Zustand for client/session state, TanStack Query for server-state caching. Feature-organized to mirror the backend's domain split. See [Frontend Architecture](architecture/frontend.md).
- **Infrastructure**: Docker Compose for local dev and production, PostgreSQL, Redis (caching/rate-limiting/token registry/Taskiq broker), Taskiq for async email delivery, Alembic for migrations, and a GitHub Actions CI workflow.
- **Error monitoring**: enabled by default via a self-hosted Bugsink container that starts with `docker compose up`. Backend (`sentry-sdk[fastapi]`) and frontend (`@sentry/react`) report to it via the Sentry SDK protocol; clear `SENTRY_DSN`/`VITE_SENTRY_DSN` to turn reporting off without stopping the container. See [Error Monitoring](error-monitoring/overview.md).

## Quickstart

Click **[Use this template](https://github.com/Nachiket-2024/mystic-auth/generate)** on GitHub to create your own repository from this one — this gives you a fresh repo with no shared git history or fork relationship to the original, so it's entirely yours from the first commit. Then clone *your* new repository and set up the environment:

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
cp .env.example .env
```

`.env.example` is prefilled with working (but obviously-fake, `change_me_in_production`-style) values for everything that isn't a real personal credential — `SECRET_KEY`, the Postgres credentials, and the Bugsink secret key/admin login all just work as-is, so `docker compose up` boots the whole stack, migrations included, straight after the copy above. Verified: a completely untouched `cp .env.example .env` brings up all six services healthy and Bugsink fully seeded. Change those dummy values before using this for anything beyond local dev, and set `APP_NAME`/`VITE_APP_NAME` if you want your own product name from the start.

Two things genuinely need your own real values, and can be filled in later — the app runs without them, but signup/login via those specific paths won't work until they're set: `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (see [OAuth setup](#oauth-setup-google) below) and `FROM_EMAIL`/`GMAIL_APP_PASSWORD` (see [Email setup](#email-setup) below).

`frontend/.env.example` → `frontend/.env` is only needed if you run the frontend locally with `npm run dev` instead of Docker — under `docker compose up`, the frontend container reads the root `.env`'s `VITE_*` values directly, so `frontend/.env` isn't read at all and can be skipped.

```bash
docker compose up
```

Once the stack is up:

- **Backend**: [http://localhost:8000/docs](http://localhost:8000/docs) — FastAPI interactive docs
- **Frontend**: [http://localhost:5173](http://localhost:5173) — Vite dev server
- **PostgreSQL**: `localhost:5433` (host-side; containers reach it at `postgres:5432` internally — the non-default host port dodges the common local-Postgres collision, see [Docker Overview](docker/overview.md))
- **Redis**: `localhost:6380` (host-side; containers reach it at `redis:6379` internally, same reasoning)
- **Bugsink**: [http://localhost:8010](http://localhost:8010) — self-hosted error monitoring UI, starts by default alongside everything above. See [Error Monitoring](error-monitoring/overview.md) if you want to turn reporting off or point at a hosted alternative instead.

Then create the reserved system superuser (one-time, CLI-only — it can never be created or promoted via any API route):

```bash
docker compose exec -it backend python -m mystic_auth.scripts.create_system_user
```

See root [`README.md`](../../README.md#-first-time-setup--creating-the-system-superuser) for the interactive prompts, and [Policy JSON Examples: system superuser policy](authorization/policy-examples.md#system-superuser-policy-seeded) for what that account can do out of the box.

## Environment configuration

Full variable-by-variable reference lives in [`.env.example`](../../.env.example) — every setting is documented inline there with a one-line comment, grouped by category (database, JWT/tokens, OAuth2, Redis, email, login protection, rate limiting, logging, environment, reverse proxy, error monitoring, frontend). Copy it to `.env` and treat that file as the source of truth, not this doc. `frontend/.env.example` also exists, but only matters if you run the frontend locally with `npm run dev`, outside Docker — under `docker compose up` (dev or prod), the frontend reads the root `.env`'s `VITE_*` values directly.

One pair is worth calling out specifically, since it's the main "make this yours" hook:

| Variable | File | Purpose |
|---|---|---|
| `APP_NAME` | `.env` | Product name used in email templates and the root `/` API response. Required — no fallback. |
| `VITE_APP_NAME` | `.env` (root) | Product name shown in the UI (navbar, auth pages) and the browser tab title (`frontend/index.html`'s `%VITE_APP_NAME%` substitution, resolved by Vite at build time). Only needs setting in `frontend/.env` too if you're running the frontend locally, outside Docker. |

## Renaming the app

Change `APP_NAME` and `VITE_APP_NAME` in the root `.env`, then restart (`docker compose up --build` if the frontend image was already built, since `VITE_APP_NAME` is baked in at build time, not read at runtime). If you're running the frontend locally with `npm run dev` instead of Docker, also update `VITE_APP_NAME` in `frontend/.env` — that path never reads the root `.env`. Nothing else in the codebase hardcodes a product name — there's no other file to touch.

**CI still uses `APP_NAME=MysticAuth`, and that's fine.** `.github/workflows/ci.yml` sets `APP_NAME` (and every other required setting) directly as a job-level environment variable, since there's no checked-in `.env` for CI to read — `Settings` refuses to start without a value for it, so CI needs *something*. That value is a placeholder for test runs, not branding: it doesn't need to match whatever you renamed the app to locally, and you don't need to touch `ci.yml` after renaming (see [CI/CD Overview](cicd/overview.md)).

## The `app/` + `mystic_auth/` split

Both the backend and the frontend are split into two top-level trees, and understanding the split is the key to customizing this template without fighting future updates from it:

- **`backend/mystic_auth/`** and **`frontend/src/mystic_auth/`** are the template's own internals — auth, PBAC, the API layer, UI components, everything described throughout the rest of `docs/mystic_auth/`. Treat this as the "pizza base": you generally don't edit it directly, you `git merge` updates into it (see [Staying in sync with upstream template updates](#staying-in-sync-with-upstream-template-updates) below).
- **`backend/app/`** and **`frontend/src/app/`** are the thin, project-specific shell: the entry point (`main.py`/`main.tsx`, `App.tsx`), and two extension files, `sdk.*` and `app_sdk.*` (below). This is where your own toppings go.

Only four files live in `backend/app/`: `main.py` (FastAPI entry point), `sdk.py` and `app_sdk.py` (below), and `__init__.py`. Only four in `frontend/src/app/`: `main.tsx`, `App.tsx`, `sdk.ts`, `app_sdk.ts`.

The docs mirror the same split: **[`docs/mystic_auth/`](README.md)** is this template's own reference documentation — upstream's, don't edit it. **[`docs/app/`](../app/README.md)** is empty by default, yours to fill with your own project's docs. Root `README.md` and `SECURITY.md` are yours too — rewrite them for your own product on day one; upstream won't touch them again after you do, so they won't conflict on future merges the way a file both sides keep editing would.

## Frontend customization

- **Design tokens / theme**: `frontend/src/mystic_auth/theme/system.ts` — Chakra UI v3 tokens (colors, semantic tokens for brand/surface/border/text). Change the `brand` color scale here to re-skin the whole app; components reference tokens (`colorPalette="brand"`, `bg="bg.surface"`, etc.), not raw hex values.
- **Pages/features**: `frontend/src/mystic_auth/` is organized by feature, one folder per domain — `auth/` (login, signup, logout, oauth2, password reset, account verification), `dashboard/`, `profile/`, `users/`, `policies/`, `audit_log/`. Each auth sub-feature is its own folder with its Page/Form/mutation-hook/types together. Import `PERMISSIONS`, `useAuthorization`, `ProtectedRoute`, `api`, etc. from `frontend/src/app/sdk.ts` (below), not from their internal locations. See [Frontend Architecture: module layout](architecture/frontend.md#module-layout) for the full table.
- **Routing**: all routes are declared in `frontend/src/app/App.tsx` — add a new `<Route>` there, wrapped in `ProtectedRoute` (optionally with a `permission` prop, see [Frontend Architecture: routing](architecture/frontend.md#routing)) and `AppLayout` if it needs the sidebar/top-bar shell.
- **State**: `frontend/src/mystic_auth/store/` — Zustand for client state (`authStore`, `themeStore`). `frontend/src/mystic_auth/core/queryClient.ts` holds the shared TanStack Query client. `frontend/src/mystic_auth/api/` holds Axios-based typed call functions per backend domain. `authStore` and `queryClient` are re-exported from `frontend/src/app/sdk.ts`.
- **Your own feature code** should live under `frontend/src/app/` (e.g. a `frontend/src/app/projects/` folder of your own), importing template pieces via `sdk.ts`/`app_sdk.ts` — not inside `frontend/src/mystic_auth/`, which stays reserved for the template's own code so upstream merges stay clean.

## The extension surface: `sdk.py`/`sdk.ts` and `app_sdk.py`/`app_sdk.ts`

`backend/app/sdk.py` and `frontend/src/app/sdk.ts` are the intended door into this template for your own domain/feature code — a single file on each side that re-exports the pieces you're meant to build on (`require_authorization`, `Permission`, `useAuthorization`, `ProtectedRoute`, the shared `api` client, `capture_exception`/`reportError` for [error monitoring](error-monitoring/overview.md), and so on). Your own code imports from `app.sdk` / `@app/sdk`, not by reaching into internal paths like `mystic_auth.authorization.dependencies.authorization_dependency` or `frontend/src/mystic_auth/authorization/useAuthorization` directly.

`backend/app/app_sdk.py` and `frontend/src/app/app_sdk.ts` are the counterpart, empty by default: the place *you* add re-exports for *your own* domain code, once you have some, kept in a separate file from `sdk.py`/`sdk.ts` specifically so a template update never conflicts with something you added.

This isn't a published package — it's just plain files, each with a docstring at the top listing everything it re-exports and why. Two things it buys you over importing internals directly everywhere:

1. **One place to read**, instead of hunting through the template's internals for "what am I actually supposed to import here."
2. **One place a merge conflict can land**, instead of many. If a future upstream update moves or renames something internal (this template's own backend and frontend went through exactly that reorganization recently — splitting into `app/` + `mystic_auth/` — see [Backend Architecture](architecture/backend.md) and [Frontend Architecture](architecture/frontend.md)), only `sdk.py`/`sdk.ts` need reconciling to match the new internal path. Your own domain code underneath it, which only ever imported from the SDK file (or your own `app_sdk.*`), doesn't need to change at all. See [Staying in sync with upstream template updates](#staying-in-sync-with-upstream-template-updates) below for why that matters.

It's deliberately *not* a full abstraction layer — it doesn't wrap or hide the underlying APIs, it just re-exports them under one stable, greppable path. You're still reading the real docs (PBAC Architecture, Authentication Overview, Frontend Architecture) to understand what each piece actually does; the SDK file only changes *where you import it from*.

## Backend customization

- **Adding your own domain/resource** (e.g. `projects`, `documents`): create it as a new top-level package under `backend/app/` (e.g. `backend/app/projects/`, sibling to `mystic_auth/`) with its own `*_model.py`, `*_schema.py`, `*_crud*.py`, and router — mounted in `backend/app/main.py`, importing `require_authorization`, `Permission`, `get_current_user`, `database`, `settings`, etc. from `backend/app/sdk.py` (above), not from their internal `mystic_auth/` locations. Keeping your own domains out of `backend/mystic_auth/` is what keeps future template updates a clean merge. See [Backend Architecture: module layout](architecture/backend.md#module-layout) for how the existing modules (`auth/`, `user_table/`, `user_crud/`) are shaped as a reference.
- **Database changes**: every schema change is an Alembic migration under `backend/alembic/versions/` — no `create_all()` anywhere. See [Database Design](database/design.md#migrations).
- **Configuration**: all settings are centralized in `backend/mystic_auth/core/settings.py` (`pydantic-settings`, env-driven) — add new settings there, never read `os.environ` directly elsewhere. Re-exported from `backend/app/sdk.py` as `settings`.

## PBAC usage

### Adding a new permission

Business-domain actions (e.g. `"projects:create"`, `"documents:view"`) don't need to go in the `Permission` enum at all — a policy can grant any action string freely. Only add an enum member in `backend/mystic_auth/authorization/permissions.py` if the action is sensitive enough that you want the privilege-escalation guard applied (see [Adding New Permissions](authorization/adding-permissions.md) for the full guidance, including how to update seed policies via a data-only migration).

### Protecting a new route

Every protected route depends on `require_authorization(action, resource_type)` — never a role check. A real, worked example, adapted from `backend/mystic_auth/api/user_routes/user_routes.py` to import from the SDK surface (above) the way your own new route module should:

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

`require_authorization(action, resource_type)` is a dependency factory (`backend/mystic_auth/authorization/dependencies/authorization_dependency.py`, re-exported from `app.sdk`) that builds the request's authorization context and calls `AuthorizationService.require(...)` for you — raising `403` if no assigned, active policy grants that action on that resource type (optionally condition-gated by time, network, ownership, etc.). For your own resources, `resource_type` doesn't need to be a `Permission` enum value at all — pass any string you want (`"projects"`, `"documents"`) and grant the matching action string via a policy (see [Writing and Testing Policies](authorization/writing-testing-policies.md#policy-creation-workflow)).

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

Covered in full in the [Deployment Guide](deployment/guide.md) — dev vs. production Compose topology, required production environment variables, database migrations, backup runbook, and free/low-cost hosting options for each of the four pieces (backend, frontend, Postgres, Redis). Production Compose file: [`docker-compose.prod.yml`](../../docker-compose.prod.yml).

## Staying in sync with upstream template updates

You cloned this repo at a point in time. This template keeps changing after that — bug fixes (like a real one: logout used to fail right after a password change, since that change revokes the session's own refresh token — fixed in `backend/mystic_auth/auth/logout/logout_handler.py`, see [Security Decisions](security/decisions.md)), new docs, small architectural cleanups. This section is how to keep pulling those in without it turning into a mess, explained from scratch — none of this assumes you already know git remotes.

### The quick way: `scripts/sync-upstream.sh`

```bash
./scripts/sync-upstream.sh
```

Run this whenever *you* decide to check for updates — nothing runs it for you automatically. It adds the `upstream` remote if it's not already there, fetches, shows you exactly what commits are incoming before touching anything, and asks for confirmation before merging. If you'd rather understand (or do) each step yourself, the rest of this section walks through exactly what the script does.

### What a "remote" is, and why you'll want two

When you `git clone` a repository, git records where you cloned it from as a **remote** named `origin` by convention. Since you created your own repository via **Use this template** and cloned *that*, `origin` already points at *your own* repo, not this original template — there's no fork relationship between the two, and no shared commit history either.

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
git merge upstream/main --allow-unrelated-histories
```

The `--allow-unrelated-histories` flag is only needed the *first* time: since your repo was created via **Use this template** rather than forked, git doesn't see any common ancestor between your history and upstream's, and refuses to merge by default as a safety check. After this first merge, the two histories share a common commit, so every merge after this one is a normal `git merge upstream/main` with no extra flag.

Aside from that one-time flag, this is a normal git merge — same mechanics as merging any other branch. If your own changes and upstream's changes touched different files (the common case, if you've been extending via new files as this doc recommends), it merges cleanly with no extra steps. If both sides touched the same lines of the same file, git stops and asks you to resolve the conflict by hand, same as any merge conflict.

### What's likely to conflict, and what almost never will

- **Your own new top-level packages/feature folders** (`backend/app/projects/`, `frontend/src/app/projects/`) — upstream has no idea they exist and will never touch them. These should essentially never conflict.
- **`backend/app/sdk.py` / `frontend/src/app/sdk.ts`** — the one place expected to occasionally conflict, and by design: if upstream moves or renames something internal (see [The extension surface](#the-extension-surface-sdkpysdkts-and-app_sdkpyapp_sdkts) above), the conflict is contained to these two files instead of scattered across every place your own code imported the old internal path directly. Resolving it here is a normal, expected part of syncing — not a sign something went wrong. `app_sdk.py`/`app_sdk.ts` should never conflict at all, since upstream never touches them.
- **Files you customized directly instead of extending** — if you added your own settings fields into the middle of `backend/mystic_auth/core/settings.py`, or edited `backend/app/main.py`'s router registration in place, or hand-edited `frontend/src/app/App.tsx`'s route list, those are exactly the files upstream is also most likely to touch over time. This is the tradeoff for customizing in place rather than through the SDK/extension points above — it's not wrong, it's just where you should expect to spend conflict-resolution time.
- **Root `README.md` and `SECURITY.md`** — upstream ships these once and then never edits them again, specifically so they never conflict once you've rewritten them for your own product. `docs/mystic_auth/` follows the same rule as the code split — you don't edit it, so it merges cleanly; `docs/app/` is yours and upstream never touches it.

### After merging

Rebuild and re-run the full test suite before trusting the merge — a merge can silently change behavior underneath you even when git resolved every conflict automatically:

```bash
docker compose up -d --build
docker compose exec -w /repo backend python -m pytest tests/backend/mystic_auth/unit tests/backend/mystic_auth/integration tests/backend/mystic_auth/security
# frontend: see docs/mystic_auth/testing/overview.md for the equivalent typecheck/lint/test/build commands
```

## Where to go next

- New to the codebase generally? Start at [`docs/mystic_auth/README.md`](README.md) for the full documentation index.
- Building your first protected feature? [Adding New Permissions](authorization/adding-permissions.md) → protect the route (above) → [Writing and Testing Policies](authorization/writing-testing-policies.md) to create and assign the policy that grants it.
- Something not behaving as documented? [PBAC Troubleshooting](authorization/troubleshooting.md) covers the most common authorization/Docker/Redis issues.

## Getting help

Stuck on something this doc set doesn't answer? Search [existing GitHub Issues](https://github.com/Nachiket-2024/mystic-auth/issues) first, then open a new one with clear reproduction steps if you can't find it. Fixes and improvements are welcome as Pull Requests — see the root [README](../../README.md#-getting-help--contributing).

**Found a security vulnerability?** Don't open a public Issue for it — see [SECURITY.md](../../SECURITY.md) for how to report it privately.
