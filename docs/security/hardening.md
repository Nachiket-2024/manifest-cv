# Security Hardening

Consolidates the concrete hardening mechanisms in the codebase — rate limiting, lockout, response headers, CORS, and cookie flags. For the *why* behind non-obvious choices, see [Security Decisions](decisions.md).

> Inherited unmodified from [mystic-auth](https://github.com/Nachiket-2024/mystic-auth), confirmed byte-identical to upstream as of this review — except `security_headers_middleware.py`, which ManifestCV extended with a narrow, well-documented carve-out for its own resume-template-preview iframe (see that file's own comments, and [Document Generation](../document-generation/overview.md)); the table below still reflects the shared, unmodified behavior for every route except that one.

## Rate limiting

`backend/app/auth/security/rate_limiter_service.py` — a generic sliding-window-by-fixed-bucket limiter backed by Redis (`INCR` + `EXPIRE` on first request in a window), applied via the `@rate_limiter_service.rate_limited("endpoint_name", account_key_func=...)` decorator on every route in `auth_routes.py` (signup, login, OAuth2 initiate/callback, `/auth/me`, logout, logout-all, password-reset request/confirm, verify-account) — and, in this repo, ManifestCV's own AI-triggering routes (`career_knowledge_routes.py`, `resume_routes.py`, see [Career Knowledge](../career-knowledge/overview.md#rate-limiting) and [Resumes](../resumes/overview.md#rate-limiting)). **Not** applied to `refresh_token_routes.py` (`POST /auth/refresh/`) — that route relies instead on its own single-use-token rotation and reuse-detection protection (see [Security Decisions](decisions.md#rate-limiting-and-lockout-are-layered-not-singular)), which a generic request-volume limiter would only duplicate.

- **Always applies a per-IP limit** (`{endpoint_name}:ip:{ip}`), resolved via [`auth/security/client_ip.py`](../authorization/architecture.md#authorization-context-builder) (trusted-proxy-aware).
- **Optionally applies a per-account limit** when `account_key_func` is given (e.g. signup/password-reset-request key on the submitted email) — closes the gap where an attacker spreads requests targeting one account across many source IPs to stay under the per-IP threshold alone.
- Both limits are configured by `MAX_REQUESTS_PER_WINDOW` / `REQUEST_WINDOW_SECONDS` (`.env.example`) — one shared threshold/window for every rate-limited endpoint, not per-endpoint tunable today (see [Concerns](../concerns/README.md)).
- **Fails closed on Redis error, reviewed and kept intentionally**: `record_request` catches all exceptions, logs them, and returns `False` ("not allowed") — a Redis outage makes every rate-limited request appear over-limit and get rejected with `429`, rather than silently disabling rate limiting. This is the opposite tradeoff from the PBAC authorization cache, which fails open to the authoritative database on a Redis error — see [PBAC Troubleshooting: Redis cache management](../authorization/troubleshooting.md#redis-cache-management) for that contrast. Practical implication: a Redis outage makes the API fully unusable for any rate-limited auth route, not just slower — see [Security Decisions](decisions.md#rate-limiter-fails-closed-on-a-redis-outage--reviewed-kept-intentionally) for why this was kept rather than changed.

## Brute-force lockout

`backend/app/auth/security/login_protection_service.py` — separate from and layered on top of the generic rate limiter (see [Security Decisions: rate limiting and lockout are layered](decisions.md#rate-limiting-and-lockout-are-layered-not-singular)):

- Per-account: `MAX_FAILED_LOGIN_ATTEMPTS` failures within `LOGIN_LOCKOUT_TIME` seconds locks that email out.
- Per-IP: `MAX_FAILED_LOGIN_ATTEMPTS_PER_IP` failures within `LOGIN_LOCKOUT_TIME_PER_IP` seconds locks that IP out across *any* account it targets.
- `check_and_record_action` double-checks `is_locked` both before and after the expensive password-hash comparison, closing a race where a concurrent request crosses the threshold mid-check.
- Both counters use `INCR`/`EXPIRE`-on-first-failure (not sliding), so the lockout window is fixed from the *first* failure, not extended by each subsequent one.

## Timing-attack resistance

See [Security Decisions: timing-attack mitigations](decisions.md#timing-attack-mitigations) — applied at login (dummy-hash comparison), signup (unconditional hashing), and password-reset-request (identical generic response).

## Security response headers

`backend/app/auth/security/security_headers_middleware.py`, applied to every response:

| Header | Value | Reasoning |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Stops MIME-type sniffing |
| `X-Frame-Options` | `DENY` | This is a JSON API with no HTML pages of its own — no framing use case exists, except ManifestCV's own resume-template-preview route (see below) |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` | Same rationale — zero functional cost since there's no HTML/script to allow, again except the preview route |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (production only — see below) | Forces HTTPS for a year, protecting the cookies from protocol downgrade |
| `Referrer-Policy` | `no-referrer` | URLs here can carry sensitive query params (OAuth2 `state`/`code`) |

**ManifestCV's one carve-out**: `GET /resumes/{id}/templates/{id}/preview` deliberately loosens `X-Frame-Options`/CSP `frame-ancestors` to name the real frontend origin (`settings.FRONTEND_BASE_URL`) instead of `DENY`/`'none'`, since the frontend embeds this specific route's PDF response in an `<iframe>` by design (see [Document Generation](../document-generation/overview.md) and `frontend/src/resumes/ResumeEditorPage.tsx`). Every other route keeps the strict upstream default — see `security_headers_middleware.py`'s own inline comments for the exact browser-compatibility reasoning (`X-Frame-Options` has no cross-origin allow-list mechanism, so CSP's `frame-ancestors` is used instead for this one route).

**HSTS is gated on `settings.ENVIRONMENT == "production"`** (checked fresh per request, not cached at import time). Sending it unconditionally would pin HSTS for a full year against real browser traffic even in a non-production deployment served over plain HTTP, with no way to turn it off short of a code change — browsers ignore the header over plain HTTP today, but that's not a reason to send a year-long pin somewhere it isn't intended to apply yet.

Note: no `Strict-Transport-Security` is set by the nginx layer serving the frontend static build (`docker/nginx.frontend.conf`) — HSTS is only emitted by the backend API responses. See [Docker Overview](../docker/overview.md).

## CORS

`backend/app/main.py` — `CORSMiddleware` allows exactly one origin (`settings.FRONTEND_BASE_URL`), `allow_credentials=True` (required for cookie-based auth to work cross-origin in dev, where frontend `:5173` and backend `:8000` are different origins), methods restricted to `GET/POST/PUT/PATCH/DELETE`, headers restricted to `Content-Type`.

## Cookies

| Cookie | Path | Flags | Set by |
|---|---|---|---|
| `access_token` | `/` | `httponly`, `secure`, `samesite=Strict` | `token_cookie_handler.py` |
| `refresh_token` | `/auth` | `httponly`, `secure`, `samesite=Strict` | `token_cookie_handler.py` |
| `oauth_state` | `/` | `httponly`, `secure`, `samesite=Lax` (must survive Google's cross-site redirect) | `oauth2_login_handler.py` |

`secure=True` on every cookie means **local HTTP development requires the browser to treat `localhost` as a secure context** (modern browsers do this automatically for `localhost`) — this will not work over plain HTTP on a non-localhost hostname.

## Middleware ordering

`main.py` adds `CORSMiddleware`, `LoggingMiddleware`, `SecurityHeadersMiddleware`, then `CorrelationIdMiddleware` last — Starlette applies middleware in reverse of add order, so `CorrelationIdMiddleware` ends up outermost, ensuring `request.state.request_id` (and the logging contextvar it sets) is populated before any other middleware or route logic runs.

## Error handling

A single global exception handler (`main.py`) catches every otherwise-unhandled exception, logs it with a full traceback, and returns a generic `500 {"detail": "Internal Server Error"}` — internal exception details never reach the client, regardless of `ENVIRONMENT`; `debug=` is never passed to the FastAPI app either (defaults `False`), so there's no path where Starlette's own debug error page could leak a traceback. See [API Reference: error responses](../api/reference.md#error-responses). This same handler also reports the exception for error monitoring (`error_monitoring.sentry_service.capture_exception`) — a no-op unless `SENTRY_DSN` is set, see [Error Monitoring](../error-monitoring/overview.md).

## Redis authentication

`REDIS_PASSWORD` (`.env`/`.env.example`) is passed to `redis-server --requirepass` in both compose files (empty value = no-op, so local dev is unaffected by default); both healthchecks authenticate with it. Since `redis-py` (`redis/client.py`) and `taskiq-redis` (`taskiq_tasks/email_tasks.py`) both authenticate via the connection URL rather than a separate kwarg, the same password must also be embedded in `REDIS_URL` (`redis://:<REDIS_PASSWORD>@redis:6379/0`) — documented inline in `.env.example`.

## `SECRET_KEY` strength enforcement

`core/settings.py` rejects any `SECRET_KEY` under 32 characters at import time (`Settings._secret_key_minimum_strength`) — a placeholder/example value fails fast at startup instead of silently signing tokens with weak entropy. This is a length floor, not a real entropy check (a 32-character low-entropy string still passes).

## Reverse-proxy IP trust

`auth/security/client_ip.py::get_client_ip` only trusts `X-Forwarded-For` when the literal TCP peer is listed in `TRUSTED_PROXY_IPS` (`.env`, empty/untrusted by default) — every rate-limit, lockout, audit-log, and PBAC context call site goes through it. Deploying behind a reverse proxy only requires setting `TRUSTED_PROXY_IPS` to that proxy's address, no code change needed.

## Known accepted gaps

See [Concerns](../concerns/README.md) for the current open list (automated backup scheduling, the single global rate-limit threshold, no deploy automation, plus ManifestCV's own product-specific items) — everything else previously tracked there has since been resolved and folded into this document. Error monitoring is available (opt-in) rather than a tracked gap now — see [Error Monitoring](../error-monitoring/overview.md).
