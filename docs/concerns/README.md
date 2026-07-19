# Known Issues, Limitations & Technical Debt

Tracked deliberately rather than left as silent gaps. Each entry reflects an active, unresolved limitation in the current implementation — nothing speculative, and nothing already fixed (resolved items live in the relevant feature documentation instead).

## Security

### Database backups are scripted, but not scheduled

**Description**: [Deployment Guide](../deployment/guide.md#backups) documents `scripts/db_backup.sh`/`scripts/db_restore.sh`, which wrap the `pg_dump`/`psql` commands (environment-driven, Docker-only, no cloud assumptions). What's still missing is a *scheduler* — these scripts still need to be wired into cron/systemd/a managed provider's backup feature/a sidecar, since no specific production host/cloud target is assumed by this template.

**Impact**: Data loss risk in any real deployment until an operator wires the scripts into a schedule.

**Why it exists**: No specific production host/cloud target is assumed by this template, so there's nothing to hang a cron job on generically.

**Possible fix**: Add a cron entry / systemd timer / managed Postgres provider's built-in backups / sidecar container that calls `scripts/db_backup.sh` on a schedule — provider-specific, left to whoever deploys this.

**Priority**: High for any real production use, N/A for local development.

## Configuration

### One global rate-limit threshold for every endpoint

**Description**: `MAX_REQUESTS_PER_WINDOW`/`REQUEST_WINDOW_SECONDS` is one shared setting applied identically to every `@rate_limited(...)` endpoint — signup, login, OAuth2, password reset, etc. (not `/auth/refresh/`, which isn't rate-limited by this mechanism at all), and now also ManifestCV's own AI-triggering routes (`career_knowledge_routes.py`, `resume_routes.py` — see [Career Knowledge](../career-knowledge/overview.md#rate-limiting) and [Resumes](../resumes/overview.md#rate-limiting)) — there's no per-endpoint override.

**Impact**: A threshold tuned for, say, login (a frequently-hit route) may be too permissive or too strict for a rarer route like password-reset-request — and the AI routes, which have a real per-call cost unlike a login attempt, currently share that exact same generic threshold rather than a deliberately-tuned one of their own.

**Why it exists**: Simplicity — one setting to reason about; the login-specific brute-force lockout (`login_protection_service.py`) layers a second, endpoint-specific control on top for the one route that most needs it.

**Possible fix**: Extend `rate_limited(...)` to accept optional per-call overrides, defaulting to the global setting.

**Priority**: Low — the current layering (generic global limit + login-specific lockout) covers the highest-risk route already.

## CI/CD

### No deploy automation

**Description**: `docker-build` in CI verifies both Dockerfiles build but does not push to a registry or deploy anywhere.

**Why it exists**: Deliberate — no assumed production target (see [Deployment Guide](../deployment/guide.md#free--low-cost-hosting-options) for provider-agnostic options); adding a deploy stage would need to assume a specific host.

**Priority**: N/A — intentional scope boundary, not a gap.

## Product (ManifestCV)

### Resume/application PDFs stored as raw bytes in Postgres, uncapped

**Description**: `resume_documents.pdf_bytes` and `application_records.pdf_snapshot` are `LargeBinary` columns with no size limit enforced anywhere in the write path.

**Impact**: A pathological or very long resume could produce an oversized PDF that bloats the row/table with no code-level cap; there's also no compression or offload to object storage.

**Why it exists**: Out of scope for the current phase — resumes are short, bounded documents in practice, so this hasn't been a real problem yet.

**Possible fix**: Enforce a reasonable max PDF size at `document_generation/resume_pdf_service.py`, or move blob storage to an object store (S3-compatible) with the DB row holding a reference instead of the bytes themselves, once/if document volume justifies it.

**Priority**: Low — no evidence yet that this is a real constraint at current usage patterns.

### Qdrant has no authentication configured

**Description**: The `qdrant` service in `docker-compose.yml`/`docker-compose.prod.yml` runs with no API key — `retrieval/qdrant_client.py` connects with a bare URL, no credential.

**Impact**: Fine on an isolated Docker network with no published port (production) or a dev-only published port (local); a genuine concern if `qdrant` is ever placed on a shared network or its port is exposed publicly, since anyone reachable could read/write any user's indexed knowledge base chunks.

**Why it exists**: Matches the current no-auth-by-default posture of `redis` in this same stack (see `REDIS_PASSWORD`) — Qdrant just doesn't have the equivalent setting wired up yet.

**Possible fix**: Add a `QDRANT_API_KEY` setting, pass it to the `qdrant` service's config, and set it on the client in `retrieval/qdrant_client.py` — mirroring how `REDIS_PASSWORD` already works.

**Priority**: Low for the default self-hosted-alongside-backend deployment (no exposed port); higher if Qdrant Cloud or any shared-network deployment is used (see [Deployment Guide: Qdrant](../deployment/guide.md#qdrant)).