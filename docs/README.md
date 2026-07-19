# Documentation

Documentation for ManifestCV, organized by feature/domain to mirror the actual code layout (`backend/app/<domain>/`, `frontend/src/<domain>/`). If something here disagrees with the code, the code wins — file an issue or update the doc.

ManifestCV is built on [mystic-auth](https://github.com/Nachiket-2024/mystic-auth) for identity/authorization — this doc set covers ManifestCV's own product features and how they're wired to that foundation, not the foundation's own internals. See [Auth & Authorization](auth/overview.md) for the boundary between the two, and mystic-auth's own docs for everything below that boundary (login, signup, OAuth2, PBAC policies, audit logging, JWT/cookie mechanics).

## Architecture

- [System Overview](architecture/system-overview.md) — whole-stack component diagram, why the stack is split this way, request lifecycle
- [Backend Architecture](architecture/backend.md) — `backend/app/` module layout (inherited + ManifestCV's own), request pipeline, middleware
- [Frontend Architecture](architecture/frontend.md) — `frontend/src/` module layout (inherited + ManifestCV's own), state management, routing, theming

## Auth & Authorization

- [Auth & Authorization](auth/overview.md) — the `mystic_auth_adapter` boundary, why it's loosely coupled, and why ManifestCV's own routes skip PBAC in favor of `user_id` scoping

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

## Docker

- [Docker Overview](docker/overview.md) — services (including `qdrant`), Dockerfiles (including the `tectonic` install), dev vs. prod compose, healthchecks, validation results

## CI/CD

- [CI/CD Overview](cicd/overview.md) — GitHub Actions workflow, jobs, what's covered and what isn't

## Deployment

- [Deployment Guide](deployment/guide.md) — dev vs. prod topology, environment variables, free/low-cost hosting options for every piece including Gemini and Qdrant

## Concerns, Limitations & Technical Debt

- [Known Issues & Future Improvements](concerns/README.md) — tracked, *unresolved* limitations only; anything already fixed lives in the relevant feature doc instead, not here

## Who this is for

Anyone adding a new ManifestCV feature, integrating a new frontend page against the API, debugging why an AI/retrieval call or a request came back the way it did, or new to the codebase and wanting the system-wide picture before touching product code. For anything about the underlying auth/PBAC layer itself, start at [Auth & Authorization](auth/overview.md) and follow its link out to mystic-auth.

## Source of truth

This documentation describes the code as it exists in `backend/app/` and `frontend/src/` at the time of writing. If something here disagrees with the code, the code wins.
