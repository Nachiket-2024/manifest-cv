# Known Issues, Limitations & Technical Debt

Tracked deliberately rather than left as silent gaps. Each entry reflects an active, unresolved limitation in the current implementation — nothing speculative, and nothing already fixed (resolved items live in the relevant feature documentation instead).

## Security

### Database backups are scripted, but not scheduled

**Description**: [Deployment Guide](../deployment/guide.md#backups) documents `scripts/db_backup.sh`/`scripts/db_restore.sh`, which wrap the `pg_dump`/`psql` commands (environment-driven, Docker-only, no cloud assumptions). What's still missing is a *scheduler* — these scripts still need to be wired into cron/systemd/a managed provider's backup feature/a sidecar, since no specific production host/cloud target is assumed by this template.

**Impact**: Data loss risk in any real deployment until an operator wires the scripts into a schedule.

**Why it exists**: No specific production host/cloud target is assumed by this template, so there's nothing to hang a cron job on generically.

**Possible fix**: Add a cron entry / systemd timer / managed Postgres provider's built-in backups / sidecar container that calls `scripts/db_backup.sh` on a schedule — provider-specific, left to whoever deploys this.

**Priority**: High for any real production use, N/A for local development.

### Qdrant is never backed up, and can silently drift from Postgres after a restore

**Description**: [Deployment Guide](../deployment/guide.md#backups) documents backing up/restoring Postgres via `scripts/db_backup.sh`/`scripts/db_restore.sh`, but Qdrant's vector index (`retrieval/qdrant_client.py`'s `career_knowledge_chunks` collection) has no backup story at all — it isn't a Docker named volume covered by any documented backup step, and Qdrant itself keeps no history.

**Impact**: Restoring Postgres from an older dump after a real incident brings back `career_knowledge_bases` rows that may no longer match what's indexed in Qdrant (rows deleted after the dump was taken still have live vectors; rows created/edited after the dump was taken are missing from Qdrant entirely) — semantic search silently returns stale or orphaned results rather than failing loudly, with no code path that detects or repairs the mismatch.

**Why it exists**: Qdrant's index is treated as a derived cache of Postgres content (`content` is the source of truth, chunks are re-embedded from it on every save — see `retrieval/knowledge_retrieval_service.py`), so it was assumed always re-derivable rather than something to actually back up.

**Possible fix**: Either add Qdrant's storage volume to the backup story, or — simpler, given it's fully derived — a documented/scripted "reindex everyone" maintenance task (loop `career_knowledge_repository` rows through `index_knowledge_base`) to run once after any Postgres restore, so a restore's runbook has an explicit, mechanical step instead of a silent gap.

**Priority**: Medium — no data loss (Postgres remains authoritative), but a real, currently-undocumented correctness gap for search results after any restore.

### Deleting a user account never cleans up their indexed knowledge-base chunks in Qdrant

**Description**: `career_knowledge_bases` rows cascade-delete in Postgres when the owning user is deleted (`ON DELETE CASCADE`, mystic-auth's own account-deletion route in `mystic_auth/api/user_routes/`), but nothing calls `retrieval/knowledge_retrieval_service.py::delete_knowledge_base(user_id)` as part of that flow — only ManifestCV's own `DELETE /career-knowledge/` route does. mystic-auth's account-deletion code has no reason to know ManifestCV's Qdrant collection exists, and giving it one would mean editing vendored mystic-auth code, which this repo deliberately never does (see [Auth & Authorization](../auth/overview.md)).

**Impact**: A deleted user's embedded career-knowledge text (raw chunk content, not just an id) is permanently orphaned in the shared `career_knowledge_chunks` Qdrant collection with no remaining code path to remove it — a data-retention/right-to-erasure gap for any deployment with real users.

**Why it exists**: Structural consequence of the mystic-auth/ManifestCV boundary — mystic-auth's account lifecycle is generic and deliberately has zero knowledge of ManifestCV's own tables or Qdrant.

**Possible fix**: A periodic reconciliation job (compare Qdrant's indexed `user_id` payload values against live `users` rows, delete orphans) is the cleanest fix that doesn't require touching mystic-auth's own code — see [Background Workers](../background-workers/taskiq.md) for where a scheduled taskiq task like this would live.

**Priority**: Medium — no security impact (chunks stay scoped to a `user_id` no route can authenticate as anymore), but a real compliance/data-retention gap.

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

### CI never smoke-tests the full multi-container stack end-to-end

**Description**: `docker-build` validates `docker compose config` (parses both compose files, checks service dependency references) and builds the backend/frontend images individually, and `real-tectonic` runs one real container against real Postgres/Redis — but no CI job runs `docker compose -f docker-compose.prod.yml up` and hits a real endpoint through the actual multi-container wiring (nginx → backend → postgres/redis/qdrant, `depends_on`/healthcheck chains, env var names actually matching between compose `environment:` blocks and what `Settings` expects).

**Impact**: A wiring bug that only manifests when every piece runs together — a typo'd env var name, a broken healthcheck dependency, an nginx `proxy_pass` misconfiguration — could pass every existing CI job and only surface on the first real deployment.

**Why it exists**: Scope/complexity tradeoff — a true end-to-end smoke test needs real service startup ordering and a working `.env` (placeholder secrets, at minimum a real-enough `GEMINI_API_KEY`/`QDRANT_URL` shape), which is a meaningfully bigger CI job than anything currently in `ci.yml`.

**Possible fix**: A new CI job that runs `docker compose -f docker-compose.prod.yml up -d` (with placeholder secrets, same pattern as the `backend` job's job-level env) and polls `/health/ready` plus the frontend's `/` before tearing down — catches wiring regressions without needing real external API access, since `/health/ready` only checks DB/Redis connectivity, not Gemini/Qdrant.

**Priority**: Medium — the individual pieces are all separately well-tested; this closes the one remaining gap between "each piece works" and "the pieces work together."

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