# Documentation

Documentation for ManifestCV, organized by feature/domain to mirror the actual code layout (`backend/app/<domain>/` + `backend/mystic_auth/<domain>/`, `frontend/src/<domain>/` + `frontend/src/mystic_auth/<domain>/`). If something here disagrees with the code, the code wins — file an issue or update the doc.

ManifestCV is built on [mystic-auth](https://github.com/Nachiket-2024/mystic-auth) for identity/authorization — this doc set covers ManifestCV's own product features and how they're wired to that foundation. See [Auth & Authorization](auth/overview.md) for the boundary between the two, and the [Foundation (mystic-auth)](#foundation-mystic-auth) section below for the inherited template's own deep-dive docs (login, signup, OAuth2, PBAC policies, audit logging, JWT/cookie mechanics) — copied in locally, verified byte-identical to upstream, rather than only linked out to GitHub.

## Architecture

- [System Overview](architecture/system-overview.md) — whole-stack component diagram, why the stack is split this way, request lifecycle
- [Backend Architecture](architecture/backend.md) — `backend/app/` (ManifestCV) + `backend/mystic_auth/` (inherited) module layout, request pipeline, middleware
- [Frontend Architecture](architecture/frontend.md) — `frontend/src/` (ManifestCV) + `frontend/src/mystic_auth/` (inherited) module layout, state management, routing, theming

## Auth & Authorization

- [Auth & Authorization](auth/overview.md) — the `mystic_auth.sdk` / `manifestcv_sdk.py` boundary, why it's loosely coupled, and why ManifestCV's own routes skip PBAC in favor of `user_id` scoping

## Foundation (mystic-auth)

Inherited unmodified from the upstream template, confirmed byte-identical as of this review — kept local rather than link-only so the deep operational detail is available offline and stays version-matched to the vendored code above.

- [Using This Repository as a Template](template-usage.md) — mystic-auth's own contract doc: what it provides, the `sdk.py`/`sdk.ts` extension surface, and how to pull in upstream updates without conflict
- [Authentication Overview](authentication/overview.md) — signup, login, refresh, logout, password reset, JWT/cookie mechanics
- [OAuth2 / PKCE](authentication/oauth2-pkce.md) — the Google login flow's PKCE/state/account-hijack-guard mechanics in full
- [PBAC Architecture](authorization/architecture.md) — the authorization request pipeline, component responsibilities, full route list
- [Adding New Permissions](authorization/adding-permissions.md) — where to define a new action, updating seed policies via data-only migrations
- [Adding New Condition Handlers](authorization/adding-condition-handlers.md) — extending the policy condition framework with a new condition type
- [Condition Schema Reference](authorization/condition-schema-reference.md) — the exact JSON shape for every policy condition type (`time`, `date_range`, `network`, `self_only`, etc.)
- [Policy JSON Examples](authorization/policy-examples.md) — worked examples, including the three seeded baseline policies
- [Writing and Testing Policies](authorization/writing-testing-policies.md) — policy creation workflow, history/rollback, unit and integration test patterns
- [PBAC Troubleshooting](authorization/troubleshooting.md) — denial debugging, Redis cache management, common Docker/Postgres connection issues
- [Security Decisions](security/decisions.md) — the *why* behind non-obvious security choices, one decision per entry
- [Security Hardening](security/hardening.md) — the concrete hardening mechanisms (rate limiting, headers, CORS, cookies) in one reference table

## Product features

- [Career Knowledge](career-knowledge/overview.md) — one private, AI-structured knowledge base per user; the source everything else is generated from
- [Resumes](resumes/overview.md) — tailored resume drafts, one per job description, AI-generated and refined against the knowledge base
- [Document Generation](document-generation/overview.md) — compiling an approved resume into a styled PDF via Markdown→LaTeX→tectonic
- [Applications](applications/overview.md) — tracked job applications, each a self-contained snapshot of the resume actually sent
- [AI & Retrieval](ai-and-retrieval/overview.md) — the Gemini (`ai_integration/`) and Qdrant (`retrieval/`) layers those features are built on

## Database

- [Database Design](database/design.md) — full schema: inherited tables plus ManifestCV's own four, and how the migration chains connect

## API

- [API Reference](api/reference.md) — ManifestCV's own route inventory, request/response shapes, and a pointer to mystic-auth's reference for the inherited routes

## Background Workers

- [Taskiq Background Workers](background-workers/taskiq.md) — broker setup, task definitions, failure handling (inherited, used unmodified for ManifestCV's own email needs)

## Testing

- [Testing Overview](testing/overview.md) — backend pytest suites (inherited + `tests/backend/manifestcv/`), frontend vitest suites (inherited + `tests/frontend/manifestcv/`), how to run both

## Error Monitoring

- [Error Monitoring](error-monitoring/overview.md) — optional, disabled by default; self-hosted Bugsink (or Sentry's hosted free tier) via the Sentry SDK protocol on both backend and frontend

## Docker

- [Docker Overview](docker/overview.md) — services (including `qdrant`, and the optional `bugsink` service), Dockerfiles (including the `tectonic` install), dev vs. prod compose, healthchecks, validation results

## CI/CD

- [CI/CD Overview](cicd/overview.md) — GitHub Actions workflow, jobs, what's covered and what isn't

## Deployment

- [Deployment Guide](deployment/guide.md) — dev vs. prod topology, environment variables, free/low-cost hosting options for every piece including Gemini and Qdrant

## Concerns, Limitations & Technical Debt

- [Known Issues & Future Improvements](concerns/README.md) — tracked, *unresolved* limitations only; anything already fixed lives in the relevant feature doc instead, not here

## Who this is for

Anyone adding a new ManifestCV feature, integrating a new frontend page against the API, debugging why an AI/retrieval call or a request came back the way it did, or new to the codebase and wanting the system-wide picture before touching product code. For anything about the underlying auth/PBAC layer itself, start at [Auth & Authorization](auth/overview.md) and follow its link out to mystic-auth.

## Source of truth

This documentation describes the code as it exists in `backend/app/`/`backend/mystic_auth/` and `frontend/src/`/`frontend/src/mystic_auth/` at the time of writing. If something here disagrees with the code, the code wins.
