# Backend Architecture

## Purpose

FastAPI application (`backend/mystic_auth/`, with the entry point and extension surface — `main.py`, `sdk.py`, `app_sdk.py` — in the sibling `backend/app/`; see [Using This Repository as a Template: the `app/` + `mystic_auth/` split](../template-usage.md#the-app--mystic_auth-split)), async throughout — SQLAlchemy async engine, async Redis client, async SMTP. One codebase, three container roles (`backend`, `taskiq_worker`, `alembic`) built from the same image with different `command:` overrides — see [Docker Overview](../docker/overview.md).

## Module layout

| Module | Purpose |
|---|---|
| `api/` | Route registration only — one `APIRouter` per feature, no business logic. Grouped: `auth_routes/`, `user_routes/`, `pbac_routes/`, `audit_log_routes/`, `health_routes/`, plus shared `route_helpers.py` |
| `auth/` | Authentication: signup, login, logout, logout-all, refresh-token rotation, password reset, account verification, Google OAuth2/PKCE, JWT/cookie handling; `auth/security/` — `client_ip.py` (trusted-proxy-aware IP resolution), `security_headers_middleware.py`, `rate_limiter_service.py`, `login_protection_service.py` — see [Authentication Overview](../authentication/overview.md) |
| `authorization/` | PBAC engine: policies, conditions, evaluator, caching, its own audit log — see [PBAC Architecture](../authorization/architecture.md) |
| `audit_log/` | Security/session-event audit log (`security_audit_log` table) — distinct from the PBAC audit log, see [Database Design](../database/design.md#why-two-audit-tables-not-one) |
| `core/` | Cross-cutting config: `settings.py` (pydantic-settings, env-driven) |
| `database/` | `connection.py` — async SQLAlchemy engine/session factory; `base.py` — declarative base |
| `emails/` | `email_template_service.py` — shared HTML email template rendering; `email_sender.py` — SMTP transport seam (swappable provider); `email_normalization.py` — canonicalizes stored/looked-up email addresses; used by the taskiq email tasks |
| `error_monitoring/` | `sentry_service.py` — error reporting via the Sentry SDK protocol (works against Sentry itself or a self-hosted compatible server, e.g. Bugsink, which runs by default). A complete no-op unless `SENTRY_DSN` is set — see [Error Monitoring](../error-monitoring/overview.md) |
| `logging/` | `logging_config.py` — `get_logger()` (structured, module-scoped loggers; INFO+ to a rotating JSON file, WARNING+ also to the terminal) and `get_startup_logger()` (a handful of one-time, boot-relevant facts — e.g. whether error monitoring is enabled — always visible in the terminal at INFO, not file-only); `correlation_id_middleware.py`, `logging_middleware.py` (request/response logging) |
| `redis/` | `client.py` — single async Redis client, shared by rate limiting, lockout, caching, token registries, and taskiq's broker |
| `scripts/` | `create_system_user.py` — one-off interactive CLI to bootstrap the reserved system account (never exposed via any API route) |
| `taskiq_tasks/` | `email_tasks.py` — the async email-sending task and its broker — see [Background Workers](../background-workers/taskiq.md) |
| `user_crud/` | `user_crud_collector.py` + `user_crud_modules/` — CRUD orchestration for the `users` table |
| `user_table/` | `user_model.py` (SQLAlchemy model, `UserRole` enum), `user_schema.py` (Pydantic schemas) |
| `main.py` | App entrypoint: middleware registration, router mounting, global exception handler, lifespan (DB pool / Redis client cleanup on shutdown) |
| `sdk.py` | Public extension surface for your own domain code (`require_authorization`, `authorization_service`, `build_authorization_context`, `Permission`, `get_current_user`, `database`, `settings`, `get_or_404`, `UserRole`, `capture_exception`) — the intended single import point for anything you build on top of this template, rather than reaching into the internal modules above directly. See [Using This Repository as a Template: the extension surface](../template-usage.md#the-extension-surface-sdkpysdkts-and-app_sdkpyapp_sdkts) |

## Request pipeline

```mermaid
flowchart TD
    Request(["Request"])
    Correlation["CorrelationIdMiddleware<br/><small>outermost — sets request.state.request_id first</small>"]
    Security["SecurityHeadersMiddleware<br/><small>attaches response headers on the way out</small>"]
    Logging["LoggingMiddleware<br/><small>logs incoming request / outgoing response</small>"]
    Cors["CORSMiddleware<br/><small>single allowed origin: FRONTEND_BASE_URL</small>"]
    Deps["Route dependency chain<br/><small>get_current_user / require_authorization,<br/>rate limiting</small>"]
    Handler["Route handler"]
    Error["Global exception handler<br/><small>@app.exception_handler(Exception) — generic 500</small>"]

    Request --> Correlation --> Security --> Logging --> Cors --> Deps --> Handler
    Handler -. "unhandled exception" .-> Error
```

Starlette applies middleware in reverse of add order, which is why `CorrelationIdMiddleware` is added *last* in `main.py` to end up *outermost* — see the inline comment there for the exact reasoning. See [Security Hardening](../security/hardening.md#middleware-ordering).

In production (`ENVIRONMENT=production`), `/docs`, `/redoc`, and `/openapi.json` are disabled entirely (`main.py`) — one less surface to lock down at a reverse proxy.

## Configuration

All configuration is centralized in `core/settings.py` (`pydantic-settings`, loaded from `.env`) — every setting is documented inline there with a one-line comment. No module reads an environment variable directly outside of `settings`. See `.env.example` for the full list, grouped by category.

## Database layer

SQLAlchemy 2.0, fully async (`asyncpg` driver). `database/connection.py`'s `Database` class wraps the async engine (`pool_pre_ping=True`, `pool_recycle=1800`) and session factory; a module-level `database` singleton is imported everywhere a session is needed (`Depends(database.get_session)`). Schema is managed entirely through Alembic migrations (`backend/alembic/versions/`) — no `create_all()` anywhere in application startup. See [Database Design](../database/design.md).

## Error handling

Two layers:
1. **Expected failures** — routes/services raise `HTTPException` with a specific status code and `detail`, or a service method returns `None`/`False` that the route translates into one.
2. **Unexpected failures** — `main.py`'s global exception handler catches anything that escapes both layers, logs the full traceback, and returns a generic `500` with no internal detail. Several service-layer methods (e.g. `signup_service.py`, `oauth2_service.py`) additionally wrap their own bodies in a broad `except Exception` so a partial failure (e.g. a database race) degrades to a clean, generic error response rather than an unhandled 500 — see [Security Decisions: the signup/OAuth2 email race](../security/decisions.md#the-signupoauth2-email-race).

## Logging

Structured, module-scoped loggers via `logging/logging_config.py::get_logger(__name__)` throughout. Every request gets a correlation ID (`CorrelationIdMiddleware`) that's attached to every log line emitted while handling it, making it possible to grep one request's full trail — routine INFO-level logging is deliberately file-only (`logs/access.log`, rotated JSON), so a request's complete trail lives there; only WARNING and above also reach `docker compose logs backend`, by design, to keep the terminal free of routine per-request noise. `get_startup_logger()` is the deliberate exception: a small, separate set of one-time facts (e.g. whether error monitoring is enabled) that are always terminal-visible at INFO, since they're boot-time config an operator would want to see immediately, not per-request volume. See [PBAC Troubleshooting: logging and debugging](../authorization/troubleshooting.md#logging-and-debugging) for the specific log-message prefixes used by the caching/audit subsystems.

## Testing coverage

`tests/backend/mystic_auth/unit/`, `integration/`, `security/`, `performance/` — see [Testing Overview](../testing/overview.md).
