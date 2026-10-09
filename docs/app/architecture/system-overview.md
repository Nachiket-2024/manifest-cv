# System Architecture
---

High-level overview of the whole stack. For deployment/runtime topology, see [../deployment/guide.md](../deployment/guide.md). For how identity/authorization fits in, see [Auth & Authorization](../auth/overview.md).

---

## Components

```mermaid
%%{init: {"themeVariables": {"lineColor": "#334155"}} }%%
flowchart TD
    Browser["Browser (SPA)"]

    Browser -- "HTTPS (TLS terminated<br/>in front; see<br/>deployment/guide.md)" --> Nginx
    Browser -- HTTPS --> Backend

    Nginx["nginx<br/>(static frontend build)"]
    Backend["FastAPI backend<br/>(uvicorn)"]

    Backend --> Postgres[("PostgreSQL<br/>users, policies, audit logs,<br/>career knowledge, workspaces,<br/>revisions, jobs, artifacts, applications")]
    Backend --> Valkey[("Valkey<br/>rate limits, refresh-token<br/>jti registry, reset/verify tokens")]
    Backend --> Qdrant[("Qdrant<br/>career knowledge chunk<br/>vectors, per-user filtered")]
    Backend --> Gemini["Gemini API<br/>(text generation + embeddings)"]
    Backend --> Bugsink["Bugsink<br/>(self-hosted error monitoring,<br/>own DB on same Postgres server)"]
    Browser -. "unhandled errors" .-> Bugsink

    Postgres <--> Procrastinate["Procrastinate worker<br/>(email, account purge,<br/>resume generation and export,<br/>queue lives in Postgres)"]
```

- **Frontend**: React + TypeScript + inherited Tailwind, shadcn, and Radix UI, plus Zustand for editor state and TanStack Query for server state. Built as a static SPA, served by nginx in production or Vite's dev server locally. Inherited from Mystic Auth and extended with ManifestCV's own Career Knowledge, Resume Studio, and Applications pages.
- **Backend**: FastAPI, async throughout (SQLAlchemy async engine, async Valkey client, async Qdrant client). One process type (`backend/app/main.py`), shared by the `backend`, `procrastinate_worker`, and `alembic` containers via the same Docker image (`docker/mystic_auth/dockerfiles/backend.Dockerfile`) with different `command:` overrides. Also runs `tectonic` (a bundled LaTeX engine) for PDF resume compilation.
- **PostgreSQL**: system of record. Users, policies, policy history, both audit log tables (inherited from mystic-auth), Procrastinate's own queue tables, plus ManifestCV's active `career_knowledge_bases`, `resume_workspaces`, `resume_revisions`, `resume_jobs`, `resume_render_artifacts`, and `application_records` tables.
- **Valkey**: ephemeral/derived state only, never the source of truth for anything that must survive a flush. Rate-limit/lockout counters, the refresh-token jti revocation registry, single-use password-reset/email-verification/OAuth2-state tokens (all with TTLs matching their expiry).
- **Procrastinate worker**: consumes a Postgres-native async task queue (no separate broker) for Mystic Auth email/account-purge tasks and ManifestCV Resume Studio generation/export jobs. Requests enqueue longer work and return a job id; the frontend polls job status. See [Background Email Delivery](../../mystic_auth/background-workers/procrastinate.md) for inherited tasks and [Resume Studio](../resumes/overview.md#background-jobs) for app jobs.
- **Qdrant**: ManifestCV's vector store. One shared collection (`career_knowledge_chunks`), isolated per user via a payload filter, holding embeddings of each user's career knowledge base sections for semantic search. See [AI & Retrieval](../ai-and-retrieval/overview.md).
- **Gemini API**: ManifestCV's AI provider. Text generation (structuring raw career input, generating/refining resumes) and embeddings (indexing/searching the knowledge base). The only external network dependency in an otherwise fully self-hosted stack.
- **Bugsink**: self-hosted error monitoring, enabled by default. Starts with `docker compose up` alongside everything else. Backend and frontend both report unhandled exceptions to it over the Sentry SDK wire protocol. Runs as its own container, using a second database on the same Postgres server (not a second Postgres instance). Inherited from mystic-auth. See [Error Monitoring](../../mystic_auth/error-monitoring/overview.md).

---

## Why this split

- **Valkey vs. Postgres**: everything in Valkey is either a cache, a rate or lockout counter, or a single-use token. Losing it on a restart degrades gracefully (a user re-requests a password reset, a rate limit resets) rather than corrupting state. Nothing that needs to survive indefinitely (users, policies, audit history, Resume Studio workspaces, applications) lives there.
- **Procrastinate**: email delivery, resume generation, and PDF export can take longer than a normal request. Queuing the work lets the API return promptly and keeps task state in Postgres without adding a separate broker.
- **One backend image, three roles**: `backend`, `procrastinate_worker`, and `alembic` all run from `docker/mystic_auth/dockerfiles/backend.Dockerfile` with different commands, rather than three separate images. Keeps dependency versions/code identical across all three by construction.
- **Qdrant alongside Postgres, not instead of it**: Postgres stores the durable, structured record (the knowledge base's actual Markdown content). Qdrant only stores derived, rebuildable vectors of that content for semantic search. Losing the Qdrant collection is a re-index away from being fixed, never data loss.

---

## Request lifecycle (authenticated request)

1. Browser sends a request with `access_token`/`refresh_token` httpOnly cookies (never accessible to frontend JS).
2. `SecurityHeadersMiddleware` and `CorrelationIdMiddleware`/`LoggingMiddleware` wrap every request (see `backend/app/main.py`).
3. `Depends(get_current_user)` (mystic-auth's dependency, imported by ManifestCV's own routes from `app.sdk`: see [Auth & Authorization](../auth/overview.md)) verifies the JWT and re-queries the user row. For PBAC-gated mystic-auth routes, `Depends(require_authorization(action, resource_type))` additionally resolves the caller's current permissions from their assigned policies. ManifestCV's own routes (Career Knowledge, Resume Studio, Applications) skip PBAC entirely. Every result is scoped by `user_id` at the query level instead.
4. On a 401 specifically, `frontend/src/mystic_auth/auth/setupAuthInterceptor.ts` attempts one silent refresh-and-retry before giving up and marking the session invalid.
5. The route handler runs. For ManifestCV's AI-backed routes, this may include a Gemini call (text generation/embedding) and/or a Qdrant call (index/search) before the response is returned. Both wrapped so a provider failure surfaces as `502 Bad Gateway`, not an unhandled `500`.

```mermaid
%%{init: {"themeVariables": {"lineColor": "#334155"}} }%%
sequenceDiagram
    participant B as Browser
    participant M as Middleware
    participant D as get_current_user
    participant R as ManifestCV route handler
    participant AI as Gemini / Qdrant

    B->>M: Request + httpOnly cookies
    M->>M: SecurityHeaders, CorrelationId, Logging
    M->>D: Pass request context
    D->>D: Verify JWT, re-query user row
    alt token expired (401)
        D-->>B: 401
        B->>B: Silent refresh + retry (once)
    else valid
        D->>R: user_id-scoped request
        opt AI-backed route
            R->>AI: generate / embed / search
            AI-->>R: result (or provider failure -> 502)
        end
        R-->>B: Response
    end
```

---

## Database design

See [Database Design](../../mystic_auth/database/design.md) for mystic-auth's inherited schema, and [ManifestCV's Own Tables](../database/design.md) for the active product tables.
