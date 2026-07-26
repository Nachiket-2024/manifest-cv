# Known Issues, Limitations & Technical Debt

Tracked deliberately rather than left as silent gaps. Each entry reflects an active, unresolved limitation in the current implementation — nothing speculative, and nothing already fixed (resolved items live in the relevant feature documentation instead).

## Security

### Database backups are scripted, but not scheduled

**Description**: [Deployment Guide](../deployment/guide.md#backups) documents `scripts/db_backup.sh`/`scripts/db_restore.sh`, which wrap the `pg_dump`/`psql` commands (environment-driven, Docker-only, no cloud assumptions). What's still missing is a *scheduler* — these scripts still need to be wired into cron/systemd/a managed provider's backup feature/a sidecar, since no specific production host/cloud target is assumed by this template.

**Impact**: Data loss risk in any real deployment until an operator wires the scripts into a schedule.

**Why it exists**: No specific production host/cloud target is assumed by this template, so there's nothing to hang a cron job on generically.

**Possible fix**: Add a cron entry / systemd timer / managed Postgres provider's built-in backups / sidecar container that calls `scripts/db_backup.sh` on a schedule — provider-specific, left to whoever deploys this.

**Priority**: High for any real production use, N/A for local development.

### `react-router-dom` carries an open high-severity advisory with no fix released yet

**Description**: [GHSA-qwww-vcr4-c8h2](https://github.com/advisories/GHSA-qwww-vcr4-c8h2) ("RSC Mode CSRF Bypass Allows Action Execution Before 400 Response") applies to `react-router` 7.12.0–8.2.0. `frontend/package.json` pins `react-router-dom: ^7.18.1`, currently the latest release — there is no newer version to bump to that resolves it, and `npm audit fix --force`'s only offered fix is downgrading to `7.11.0`, seven releases back.

**Impact**: `npm audit --audit-level=high` fails on this finding alone. The advisory itself is scoped to React Router's RSC (React Server Components) data mode; this template is a plain client-side SPA (`createBrowserRouter`, no RSC), so the vulnerable code path isn't exercised here — but `npm audit` flags the package version, not actual usage, so it can't tell the difference.

**Why it exists**: Upstream hasn't shipped a patched 7.x or 8.x release yet. Downgrading to dodge the version range would trade a very likely inapplicable advisory for real regressions from seven skipped releases.

**Possible fix**: Bump `react-router-dom` once upstream ships a patched release in the 7.x/8.x line. Until then, `.github/workflows/ci.yml`'s npm audit step is `continue-on-error: true` specifically for this reason (see the comment there) — re-tighten it back to blocking once this is resolved.

**Priority**: Low — believed not exploitable given this app never uses RSC mode, but tracked so the CI exception doesn't silently mask a future, genuinely-relevant high-severity finding.

## Configuration

### One global rate-limit threshold for every endpoint

**Description**: `MAX_REQUESTS_PER_WINDOW`/`REQUEST_WINDOW_SECONDS` is one shared setting applied identically to every `@rate_limited(...)` endpoint (signup, login, OAuth2, password reset, etc. — not `/auth/refresh/`, which isn't rate-limited by this mechanism at all) — there's no per-endpoint override.

**Impact**: A threshold tuned for, say, login (a frequently-hit route) may be too permissive or too strict for a rarer route like password-reset-request.

**Why it exists**: Simplicity — one setting to reason about; the login-specific brute-force lockout (`login_protection_service.py`) layers a second, endpoint-specific control on top for the one route that most needs it.

**Possible fix**: Extend `rate_limited(...)` to accept optional per-call overrides, defaulting to the global setting.

**Priority**: Low — the current layering (generic global limit + login-specific lockout) covers the highest-risk route already.

## CI/CD

### No deploy automation

**Description**: `docker-build` in CI verifies both Dockerfiles build but does not push to a registry or deploy anywhere.

**Why it exists**: Deliberate — this is a template repository with no assumed production target (see [Deployment Guide](../deployment/guide.md#free--low-cost-hosting-options) for provider-agnostic options); adding a deploy stage would need to assume a specific host.

**Priority**: N/A — intentional scope boundary, not a gap.