# Known Issues, Limitations & Technical Debt
---

Tracked deliberately rather than left as silent gaps. Each entry reflects an active, unresolved limitation in the current implementation. Nothing speculative, and nothing already fixed (resolved items live in the relevant feature documentation instead).

> Diagram omitted. This page is an index of independent limitations rather than a process flow.

---

## Security

### Database backups are scripted, but not scheduled

**Description**: [Deployment Guide](../deployment/guide.md#backups) documents `scripts/mystic_auth/db/database-backup/database-backup.sh`/`scripts/mystic_auth/db/database-restore/database-restore.sh`, which wrap the `pg_dump`/`psql` commands. They are environment-driven, Docker-only, and cloud-agnostic. What's still missing is a *scheduler*. These scripts still need to be wired into cron, systemd, a managed provider's backup feature, or a sidecar, since no specific production host/cloud target is assumed by this project.

**Impact**: Data loss risk in any real deployment until an operator wires the scripts into a schedule.

**Why it exists**: No specific production host/cloud target is assumed by this project, so there's nothing to hang a cron job on generically.

**Possible fix**: Add a cron entry, systemd timer, managed Postgres backup, or sidecar container that calls `scripts/mystic_auth/db/database-backup/database-backup.sh` on a schedule. This is provider-specific and left to whoever deploys this.

**Priority**: High for any real production use, N/A for local development.

### Qdrant is never backed up, and can silently drift from Postgres after a restore

**Description**: [Deployment Guide](../deployment/guide.md#backups) documents backing up/restoring Postgres via `scripts/mystic_auth/db/database-backup/database-backup.sh`/`scripts/mystic_auth/db/database-restore/database-restore.sh`, but Qdrant's vector index (`retrieval/qdrant_client.py`'s `career_knowledge_chunks` collection) has no backup story. It isn't a Docker named volume covered by any documented backup step, and Qdrant itself keeps no history.

**Impact**: Restoring Postgres from an older dump after a real incident brings back `career_knowledge_bases` rows that may no longer match what's indexed in Qdrant (rows deleted after the dump was taken still have live vectors. Rows created/edited after the dump was taken are missing from Qdrant entirely). Semantic search silently returns stale or orphaned results rather than failing loudly, with no code path that detects or repairs the mismatch.

**Why it exists**: Qdrant's index is treated as a derived cache of Postgres content (`content` is the source of truth, chunks are re-embedded from it on every save. See `retrieval/knowledge_retrieval_service.py`), so it was assumed always re-derivable rather than something to actually back up.

**Possible fix**: Either add Qdrant's storage volume to the backup story, or, simpler given it's fully derived, a documented/scripted "reindex everyone" maintenance task (loop `career_knowledge_repository` rows through `index_knowledge_base`) to run once after any Postgres restore, so a restore's runbook has an explicit, mechanical step instead of a silent gap.

**Priority**: Medium. No data loss (Postgres remains authoritative), but a real, currently-undocumented correctness gap for search results after any restore.

### Deleting a user account never cleans up their indexed knowledge-base chunks in Qdrant

**Description**: `career_knowledge_bases` rows cascade-delete in Postgres when the owning user is deleted (`ON DELETE CASCADE`, mystic-auth's own account-deletion route in `mystic_auth/api/user_routes/`), but nothing calls `retrieval/knowledge_retrieval_service.py::delete_knowledge_base(user_id)` as part of that flow. Only ManifestCV's own `DELETE /career-knowledge/` route does. Mystic-auth's account-deletion code has no reason to know ManifestCV's Qdrant collection exists, and giving it one would mean editing vendored mystic-auth code, which this repo deliberately never does (see [Auth & Authorization](../auth/overview.md)).

**Impact**: A deleted user's embedded career-knowledge text (raw chunk content, not just an id) is permanently orphaned in the shared `career_knowledge_chunks` Qdrant collection with no remaining code path to remove it. A data-retention/right-to-erasure gap for any deployment with real users.

**Why it exists**: Structural consequence of the mystic-auth/ManifestCV boundary. Mystic-auth's account lifecycle is generic and deliberately has zero knowledge of ManifestCV's own tables or Qdrant.

**Possible fix**: A periodic reconciliation job (compare Qdrant's indexed `user_id` payload values against live `users` rows, delete orphans) is the cleanest fix that doesn't require touching mystic-auth's own code. See [Background Email Delivery](../../mystic_auth/background-workers/procrastinate.md) for where a scheduled Procrastinate task like this would live, alongside the existing daily account-purge job.

**Priority**: Medium. No security impact (chunks stay scoped to a `user_id` no route can authenticate as anymore), but a real compliance/data-retention gap.

---

## Configuration

---

## CI/CD

### No deploy automation

**Description**: `docker-build` in CI verifies both Dockerfiles build but does not push to a registry or deploy anywhere.

**Why it exists**: Deliberate. No assumed production target (see [Deployment Guide](../deployment/guide.md#free--low-cost-hosting-options) for provider-agnostic options). Adding a deploy stage would need to assume a specific host.

**Priority**: N/A. Intentional scope boundary, not a gap.

### CI never smoke-tests the prod/local-prod multi-container wiring specifically (only dev)

**Description**: `docker-build` now validates `docker compose config` for all five compose files, builds both images, and boots the real **dev** stack (`postgres`, `valkey`, app-owned `qdrant`, `alembic`, `backend`, `frontend`, `procrastinate_worker`) to confirm `/health/ready` and the frontend both actually respond through real service wiring - this used to be a documented gap, now closed for the dev shape. What's still unverified in CI is the **prod**/**local-prod** wiring specifically: nginx's `proxy_pass` to `backend`, Caddy's/the tunnel container's reverse-proxying to `frontend:80`, and the prod-only env vars (`TRUSTED_PROXY_IPS` derivation, `UVICORN_WORKERS`, etc.) that dev's compose file doesn't exercise at all.

**Impact**: A wiring bug specific to the prod/local-prod shape (an nginx misconfiguration, a Caddy/tunnel reverse-proxy issue, a prod-only env var mismatch) could pass every existing CI job, including the now-fixed dev smoke test, and only surface on the first real deployment.

**Why it exists**: Scope/complexity tradeoff. A true prod-shaped smoke test needs TLS-adjacent setup (or a way to skip it) and a working `env/mystic_auth/.env.prod`-shaped config, a meaningfully bigger CI job than the dev-stack boot `docker-build` already does.

**Possible fix**: Extend `docker-build` (or a new job) to also boot `docker-compose.prod.yml` with placeholder secrets and a self-signed/skipped-TLS mode, polling `/health/ready` through nginx/Caddy rather than direct to `backend`.

**Priority**: Low. The piece most likely to actually break (backend/frontend/DB/Valkey/Qdrant wiring) is already covered by the dev-stack smoke test; what's left is the reverse-proxy layer specifically.

---

## Product (ManifestCV)

### Resume/application PDFs stored as raw bytes in Postgres, uncapped

**Description**: Export artifacts and application PDF snapshots can become large, and the write path still needs a hard size limit or object storage policy.

**Impact**: A pathological or very long resume could produce an oversized PDF that bloats the row/table with no code-level cap. There's also no compression or offload to object storage.

**Why it exists**: Out of scope for the current phase. Resumes are short, bounded documents in practice, so this hasn't been a real problem yet.

**Possible fix**: Enforce a reasonable max PDF size at the Resume Studio export service, or move artifact storage to an object store with the database row holding a reference instead of the bytes themselves, once document volume justifies it.

**Priority**: Low. No evidence yet that this is a real constraint at current usage patterns.

### Qdrant has no authentication configured

**Description**: The `qdrant` service in all five compose files (`docker-compose.dev.yml`, each `docker-compose.local-prod-*.yml`, `docker-compose.prod.yml`) runs with no API key. `retrieval/qdrant_client.py` connects with a bare URL, no credential.

**Impact**: Fine on an isolated Docker network with no published port (production) or a dev-only published port (local). A genuine concern if `qdrant` is ever placed on a shared network or its port is exposed publicly, since anyone reachable could read/write any user's indexed knowledge base chunks.

**Why it exists**: Matches the current no-auth-by-default posture of `valkey` in this same stack (see `VALKEY_PASSWORD`). Qdrant just doesn't have the equivalent setting wired up yet.

**Possible fix**: Add a `QDRANT_API_KEY` setting, pass it to the `qdrant` service's config, and set it on the client in `retrieval/qdrant_client.py`: mirroring how `VALKEY_PASSWORD` already works.

**Priority**: Low for the default self-hosted-alongside-backend deployment (no exposed port). Higher if Qdrant Cloud or any shared-network deployment is used (see [Deployment Guide: Qdrant](../deployment/guide.md#qdrant)).
