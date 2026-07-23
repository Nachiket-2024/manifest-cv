# Error Monitoring

Optional, disabled by default. This template ships the wiring to report unhandled backend exceptions and frontend render crashes to an error-tracking service — but makes zero SDK calls, and adds zero bytes to the frontend bundle, unless you explicitly turn it on.

## Why Bugsink

Both the backend and frontend integrations speak the **Sentry SDK wire protocol** — the same protocol Sentry itself, [GlitchTip](https://glitchtip.com/), and [Bugsink](https://www.bugsink.com/) all implement. Nothing here is tied to Sentry-the-company specifically; only the SDK package names (`sentry-sdk`, `@sentry/react`) are.

This template documents **self-hosted Bugsink** as the default path, for reasons specific to what this template is:

- **This is an auth + PBAC template.** Error payloads (stack traces, request context) can carry emails and other PII. Self-hosting keeps that data on your own infrastructure instead of a third-party SaaS by default.
- **Lightweight.** Bugsink is a single Django app — no Redis, no Celery, no split frontend/backend containers. It reuses the same Postgres server this template already runs (a second database, not a second container — see `docker/postgres-init/init-bugsink-db.sh`).
- **No hard event cap that silently drops data.** Self-hosted, there's no monthly quota — you won't lose visibility into an incident right when a traffic spike would otherwise blow through a SaaS free tier's limit.
- **License**: Bugsink is [PolyForm Shield](https://polyformproject.org/licenses/shield/1.0.0/) — source-available, not OSI-approved open source. In plain terms: free to self-host and modify, with one restriction — you can't use it to build a *competing* error-tracking product. Using it to monitor errors in an unrelated app (this one) isn't a competing use, so this doesn't affect you or this template's own MIT license (Bugsink runs as a fully separate service you only talk to over HTTP — nothing from it is copied into or distributed with this repo).

Prefer Sentry's own hosted free tier instead? It works identically — see [Alternative: Sentry's hosted free tier](#alternative-sentrys-hosted-free-tier) below. Same SDK, same code, just a different DSN.

## Quickstart (self-hosted Bugsink)

No external account or sign-up is involved anywhere in this path — Bugsink is entirely self-hosted, and the only "credentials" are the superuser login you make up yourself in step 1. (Compare with [the Sentry-hosted alternative](#alternative-sentrys-hosted-free-tier) below, which does need a sentry.io account — that's the one path here that involves a third party.)

**`docker compose up` alone never starts Bugsink** — see [Docker Overview: services](../docker/overview.md#services) for why (it's a separate opt-in profile, by design, so this template's default footprint doesn't grow for everyone who doesn't want it). If you ran the normal quickstart and don't see a `bugsink` container, that's expected, not a failure — proceed with step 2 below.

1. **Set the Bugsink-specific variables in `.env`** (see `.env.example`):

   ```bash
   BUGSINK_SECRET_KEY=<run: openssl rand -base64 50>
   BUGSINK_SUPERUSER_EMAIL=<your email>
   BUGSINK_SUPERUSER_PASSWORD=<a strong password>
   BUGSINK_BASE_URL=http://localhost:8010
   ```

   These configure the Bugsink *container* directly — they are unrelated to this app's own `Settings` class and never read by the backend/frontend themselves. `BUGSINK_BASE_URL` is what Bugsink uses to construct links back to itself (e.g. in any email it sends) — `http://localhost:8010` is only correct for local dev; update it to match wherever you're actually reaching Bugsink from (a LAN IP, a tunnel, a real hostname) if that's not `localhost`.

2. **Start it** (never starts as part of a plain `docker compose up` — this is what makes it opt-in):

   ```bash
   docker compose --profile monitoring up -d
   ```

   (`--profile monitoring up -d` with no service name also brings up everything else normally started by `docker compose up -d` — `bugsink` is simply added to that set, not a replacement for it. Append ` bugsink` instead if you only want to (re)start that one container without touching the rest of the stack.)

   First boot runs Bugsink's own database migrations against the `bugsink` database (created automatically by `docker/postgres-init/init-bugsink-db.sh` — see that file's own comment if you're enabling this against an *already-initialized* `postgres_data` volume, since init scripts only run once, against a fresh volume), creates the superuser from step 1, and then a second one-shot `seed_bugsink_project` container seeds a default Team + Project (see [Default project & team](#default-project--team) below) so there's already something to click into.

3. **Log in** at `http://localhost:8010` (or whatever `BUGSINK_BASE_URL` you set) with the superuser credentials from step 1 — a project named after `APP_NAME` is already there, created automatically (see below), so there's no "New Project" step to figure out first. Open it and go to its settings to find its **DSN** — a URL like `http://<key>@localhost:8010/1`.

4. **Put that DSN in `.env`** — both `SENTRY_DSN` (backend) and `VITE_SENTRY_DSN` (frontend) live in the same root `.env` now, but still need **two different hosts, not the same DSN copy-pasted into both**:

   ```bash
   # SENTRY_DSN — the backend runs *inside* the Docker network, where
   # "localhost" means the backend container itself, not Bugsink. Reach
   # Bugsink via its Compose service name and internal container port instead:
   SENTRY_DSN=http://<key>@bugsink:8000/1

   # VITE_SENTRY_DSN — the frontend SDK runs in the browser, on your host
   # machine, outside Docker entirely, so it uses the published host port
   # Bugsink's DSN actually gave you:
   VITE_SENTRY_DSN=http://<key>@localhost:8010/1
   ```

   This is a real, easy-to-miss trap — Bugsink's UI only ever shows you the `localhost:8010` form (correct for the frontend), since it has no way to know it's also being reached by a *server* running in a sibling container. Using that same `localhost:8010` DSN for `SENTRY_DSN` looks correct, passes `init_sentry()`'s own validation, and then silently sends nothing — `sentry-sdk`'s background transport swallows the connection-refused error, so nothing shows up in Bugsink and nothing shows up in your own logs either. If backend events aren't appearing, this is the first thing to check.

5. **Restart backend and frontend** so they pick up the new env vars:

   ```bash
   docker compose up -d --build backend frontend
   ```

6. **Verify it actually works** — don't just trust the config, trigger a real error and confirm it shows up in Bugsink's UI:

   ```bash
   docker compose exec backend python -c "
   import sentry_sdk
   from mystic_auth.error_monitoring.sentry_service import init_sentry, capture_exception
   import asyncio

   init_sentry()
   try:
       raise ValueError('manual verification error')
   except ValueError as exc:
       asyncio.run(capture_exception(exc))
   sentry_sdk.flush(timeout=10)  # the SDK sends asynchronously — without an explicit
                                  # flush, this one-off script can exit before the
                                  # background transport thread gets to send anything
   "
   ```

   Open your project in Bugsink within a few seconds and confirm a `ValueError: manual verification error` Issue appeared. Delete it afterward from Bugsink's own UI (Issue → delete) — this is a one-time sanity check, not something to leave sitting in your issue list. (Deleting it via Django's ORM/shell directly, rather than Bugsink's own UI, can hit foreign-key errors from related tables it doesn't cascade through automatically — the UI's delete action handles this correctly, a raw ORM `.delete()` may not.)

To turn it off again: clear `SENTRY_DSN`/`VITE_SENTRY_DSN` (or just don't set them) — every capture call becomes a no-op immediately, no restart of Bugsink itself required. The `bugsink` container can keep running or be stopped independently (`docker compose --profile monitoring stop bugsink`).

## Default project & team

Bugsink itself ships with no seed data — a brand-new instance has no Team, no Project, and (correctly) no Issues. That's the right default for *events*, but it also means the first thing a login sees is an empty shell with no obvious next step: nothing to click, and no built-in explanation of what a "Team" even is before you're allowed to create a "Project" inside one.

A second one-shot service, `seed_bugsink_project` (`docker-compose.yml`/`docker-compose.prod.yml`, script at `docker/bugsink-seed/seed_default_project.py`), fixes this by idempotently creating exactly one Team and one Project — both named after `APP_NAME` — and making the superuser from step 1 an accepted admin of both, every time `docker compose --profile monitoring up` runs:

- **Idempotent, not destructive.** It only acts when zero non-deleted projects exist anywhere in the Bugsink instance. Create more projects/teams by hand afterward (multiple services, staging vs. prod, whatever) and this script permanently no-ops on every future run — it never touches, renames, or recreates anything once a project exists.
- **Why a script piped into `bugsink-manage shell` rather than a proper management command**: Bugsink's official image exposes no hook for adding custom Django management commands, and the model-level creation calls used here (`Team.objects.get_or_create`, `ProjectMembership.objects.get_or_create`, etc.) are the same primitives Bugsink's own project-creation view uses internally — there's no supported REST/CLI shortcut for "create a project non-interactively" as of this template's mystic-auth/Bugsink versions.
- **Runs after `bugsink` reports healthy** (`depends_on: condition: service_healthy`), so it always sees fully-migrated tables; runs before `backend`/`frontend` even start, so the very first login already has something to open. No restart policy, same reasoning as `alembic`.
- **Doesn't touch `SENTRY_DSN`/`VITE_SENTRY_DSN` for you.** It prints the new project's DSN to its own container's log output (`docker compose logs seed_bugsink_project`) as a convenience, but wiring that DSN into `.env` (both `SENTRY_DSN` and `VITE_SENTRY_DSN`) is still the manual step in [Quickstart](#quickstart-self-hosted-bugsink) above — the two host forms it needs (`bugsink:8000` internally vs. `localhost:8010` from the browser) aren't something a script running *inside* the Bugsink container can know about your setup.
- **Opting out**: if you'd rather organize projects/teams entirely by hand, just create your own before ever starting `seed_bugsink_project` (e.g. via Bugsink's UI right after your first login) — the idempotency check means the bootstrap script will find your project and do nothing.

## Using Bugsink

Written for whoever's never touched Bugsink (or Sentry, or any error tracker like this) before — the concepts, not a pixel-perfect UI tour, since the UI itself is simple enough that "what am I even looking at" is the only real barrier.

- **Issues, not raw events.** Once error reporting is on, you don't watch a live feed — you open `http://localhost:8010` (or wherever `BUGSINK_BASE_URL` points) and check your project's **Issues** list when you actually want to know what's broken. An Issue is one *kind* of error, automatically deduplicated — the same exception happening 500 times shows up as one Issue with a count of 500, not 500 separate rows. That count, plus "first seen"/"last seen" timestamps, is usually enough on its own to tell a one-off blip from something actively breaking right now.
- **Opening an Issue** shows the exception type and message, the full stack trace (which file/line/function, down to the frame that actually raised it), and — for backend errors — the caller's email if `capture_exception` could resolve one from their session (see [User context](#user-context) below). There's no request-body/header dump beyond that; this integration deliberately doesn't send that (see [Security notes](#security-notes)).
- **Resolving an Issue** marks it as fixed — it moves out of your default "unresolved" view. If the exact same error happens again later, Bugsink reopens it automatically (a "regression") rather than silently starting a fresh, disconnected Issue — so resolving something is a real claim ("I fixed this"), not just archiving it.
- **Muting an Issue** is different from resolving: use it for something you've deliberately decided isn't worth fixing right now (a known third-party flake, noise from an edge case you're accepting) — it stays out of your unresolved view without claiming you fixed anything.
- **Projects and teams**: one Bugsink instance can hold multiple projects (e.g. if you later stand up another service pointed at the same Bugsink), each with its own DSN and its own Issues list, grouped under teams for who can see what. For a single-app setup like this template's default, one project is all you need.
- **You won't see anything until something actually breaks.** There's no seed data — a fresh project's Issues list is empty by design. If you want to confirm the pipe works before waiting for a real bug, use the verification command in step 6 above.

## What gets reported, and from where

| Layer | Trigger | Where |
|---|---|---|
| Backend | Any exception that reaches `main.py`'s global exception handler (i.e. anything not already turned into a normal HTTP error response by a route) | `backend/mystic_auth/error_monitoring/sentry_service.py::capture_exception` |
| Backend (manual) | Anything your own route/service code catches but still wants tracked | `capture_exception`, re-exported from `backend/mystic_auth/sdk.py` |
| Frontend | An uncaught render error anywhere in the component tree | `frontend/src/mystic_auth/ui/ErrorBoundary.tsx` → `core/errorMonitoring.ts::reportError` |
| Frontend (manual) | Anything your own component/hook code catches but still wants tracked | `reportError`, re-exported from `frontend/src/mystic_auth/sdk.ts` |
| Frontend (automatic) | Uncaught `window.onerror`/unhandled promise rejections | Sentry SDK's own default browser instrumentation, once initialized |

**Not reported automatically**: a normal `403`/`404`/validation error — those are expected API responses handled by the calling code (a toast, an inline `FormAlert`), not exceptions. Reporting every expected error response would drown out the events that actually indicate a bug.

## User context

The backend attaches the caller's email (read from their `access_token` cookie, best-effort — a missing/expired/invalid cookie just means no user context, never a failure to capture) so an error can be traced back to who hit it. Deliberately narrow: only an email is attached, not the SDK's broader automatic PII collection (request bodies, full cookie jars, etc.), which could otherwise capture credentials in transit — see `error_monitoring/sentry_service.py::init_sentry`'s own comment on `send_default_pii`.

## Security notes

- **Bugsink needs its own operational security**, same as Postgres/Redis already do in this stack — self-hosting only guarantees the *data* stays on your infrastructure, not that the service is automatically locked down. It has no host port exposed at all in `docker-compose.prod.yml` by default (unlike backend/frontend, which are meant to be internet-facing) — reaching it in production means an SSH tunnel, a VPN, or a reverse-proxy route you add deliberately, not something exposed by default.
- **Traces are 0% sampled** (`traces_sample_rate: 0` / `tracesSampleRate: 0`) — this integration is error capture only, not performance monitoring/tracing. No request-body/timing data is sent beyond what an actual captured exception includes.
- **`SECRET_KEY` vs. `BUGSINK_SECRET_KEY`**: these are two unrelated secrets for two unrelated purposes (this app's JWT signing key vs. Bugsink's own Django secret key) — never reuse one for the other.
- **A typo'd `SENTRY_DSN` can't take the app down.** `init_sentry()` runs at import time, before the app itself really exists — it deliberately catches any failure from `sentry_sdk.init()` (verified directly: a malformed DSN string does raise from the SDK) and logs a warning instead of letting it propagate, so a mistake in this one *optional* setting degrades to "monitoring is off" rather than "nothing works." See [Security Decisions](../security/decisions.md#a-malformed-sentry_dsn-must-never-crash-the-app).

## Alternative: Sentry's hosted free tier

Since the integration only depends on the Sentry SDK protocol, pointing it at Sentry's own hosted service instead of self-hosted Bugsink is purely a matter of using a different DSN — no code changes:

1. Create a free account at [sentry.io](https://sentry.io) and a project.
2. Copy that project's DSN into **both** `SENTRY_DSN` and `VITE_SENTRY_DSN` — identically this time. Sentry's hosted DSN is a real internet hostname (`https://<key>@o0.ingest.sentry.io/...`), reachable the same way from the backend container and the browser, so the self-hosted Bugsink split (step 4 above, `bugsink:8000` internally vs. `localhost:8010` from the browser) doesn't apply here.
3. Skip the `bugsink` Docker service entirely — you don't need it.

Trade-offs vs. self-hosted Bugsink: zero infrastructure to run/maintain, a more polished/mature UI — but error data (including any PII it contains) leaves your infrastructure, and the free tier caps at 5,000 events/month with events silently dropped past that (1 dashboard user).

## Alternative: GlitchTip

[GlitchTip](https://glitchtip.com/) is another real option if you outgrow Bugsink or prefer a fully OSI-approved-open-source (MIT) self-hosted alternative — same DSN-swap story, but heavier to run (needs Redis + Celery + a split frontend/backend on top of Postgres, vs. Bugsink's single container). Not documented step-by-step here since Bugsink already covers the "lightweight, self-hosted, license-compatible" niche this template optimizes for — but nothing in the integration code assumes Bugsink specifically.
