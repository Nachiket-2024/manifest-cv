# Documentation

Documentation for ManifestCV, organized by feature/domain to mirror the actual code layout (`backend/app/<domain>/` + `backend/mystic_auth/<domain>/`, `frontend/src/app/<domain>/` + `frontend/src/mystic_auth/<domain>/`). If something here disagrees with the code, the code wins, so file an issue or update the doc.

ManifestCV is built on [mystic-auth](https://github.com/Nachiket-2024/mystic-auth) for identity/authorization. This doc set covers ManifestCV's own product features and how they're wired to that foundation. See [Auth & Authorization](auth/overview.md) for the boundary between the two, and the [Foundation (mystic-auth)](#foundation-mystic-auth) section below for the inherited template's own deep-dive docs (login, signup, OAuth2, PBAC policies, audit logging, JWT/cookie mechanics), mirrored locally under [`docs/mystic_auth/`](../mystic_auth/README.md) rather than only linked out to GitHub.

---

## Architecture

- [System Overview](architecture/system-overview.md): whole-stack component diagram, why the stack is split this way, request lifecycle
- [Backend Architecture](architecture/backend.md): `backend/app/` (ManifestCV) + `backend/mystic_auth/` (inherited) module layout, request pipeline, middleware
- [Frontend Architecture](architecture/frontend.md): `frontend/src/app/` (ManifestCV) + `frontend/src/mystic_auth/` (inherited) module layout, state management, routing, theming

---

## Auth & Authorization

- [Auth & Authorization](auth/overview.md). The `app/sdk.py` / `app/app_sdk.py` boundary, why it's loosely coupled, and why ManifestCV's own routes skip PBAC in favor of `user_id` scoping

---

## Foundation (mystic-auth)

Inherited unmodified from the upstream template. Mirrored locally under [`docs/mystic_auth/`](../mystic_auth/README.md) rather than only linked out to GitHub, so the deep operational detail is available offline and stays version-matched to the vendored code. Don't edit these directly. They're the template's own docs, refreshed wholesale from upstream.

- [mystic-auth docs index](../mystic_auth/README.md). The full inherited doc set: template usage/extension surface, authentication flows, OAuth2/PKCE, PBAC architecture and troubleshooting, adding permissions/conditions, security decisions/hardening, background workers, error monitoring
- [Using This Repository as a Template](../mystic_auth/template-usage/overview.md). Mystic-auth's own contract doc: what it provides, the `sdk.py`/`app_sdk.py` extension surface, and how to pull in upstream updates without conflict

---

## Product features

- [Career Knowledge](career-knowledge/overview.md). One private, AI-structured knowledge base per user. The source everything else is generated from
- [Resumes](resumes/overview.md). Tailored resume drafts, one per job description, AI-generated and refined against the knowledge base
- [Document Generation](document-generation/overview.md). Compiling an approved resume into a styled PDF via Markdown to LaTeX to tectonic
- [Applications](applications/overview.md). Tracked job applications, each a self-contained snapshot of the resume actually sent
- [AI & Retrieval](ai-and-retrieval/overview.md). The Gemini (`ai_integration/`) and Qdrant (`retrieval/`) layers those features are built on

---

## Database

- [Database Design](../mystic_auth/database/design.md). Mystic-auth's own inherited schema (users, PBAC policies, audit logs)
- [ManifestCV's Own Tables](database/design.md). The four product tables (`career_knowledge_bases`, `resume_drafts`, `resume_documents`, `application_records`), ERD, and how the migration chains connect

---

## API

- [API Reference](api/reference.md). ManifestCV's own route inventory, request/response shapes, and a pointer to mystic-auth's own reference (mirrored at [`docs/mystic_auth/api/reference.md`](../mystic_auth/api/reference.md)) for the inherited routes

---

## Testing

- [Testing Overview](testing/overview.md). Backend pytest suites (inherited `tests/backend/mystic_auth/` + `tests/backend/app/`), frontend vitest suites (inherited `tests/frontend/mystic_auth/` + `tests/frontend/app/`), how to run both

---

## Docker

- [Docker Overview](docker/overview.md). Services (including `qdrant`, and `bugsink`, which starts by default), Dockerfiles (including the `tectonic` install), dev vs. Prod compose, healthchecks, validation results

---

## CI/CD

- [CI/CD Overview](cicd/overview.md). GitHub Actions workflow, jobs, what's covered and what isn't

---

## Deployment

- [Deployment Guide](deployment/guide.md). Dev vs. Prod topology, environment variables, free/low-cost hosting options for every piece including Gemini and Qdrant

---

## Concerns, Limitations & Technical Debt

- [Known Issues & Future Improvements](concerns/README.md). Tracked, *unresolved* limitations only. Anything already fixed lives in the relevant feature doc instead, not here

---

## Who this is for

Anyone adding a new ManifestCV feature, integrating a new frontend page against the API, debugging why an AI/retrieval call or a request came back the way it did, or new to the codebase and wanting the system-wide picture before touching product code. For anything about the underlying auth/PBAC layer itself, start at [Auth & Authorization](auth/overview.md) and follow its links into [`docs/mystic_auth/`](../mystic_auth/README.md).

---

## Source of truth

This documentation describes the code as it exists in `backend/app/`/`backend/mystic_auth/` and `frontend/src/app/`/`frontend/src/mystic_auth/` at the time of writing. If something here disagrees with the code, the code wins.
