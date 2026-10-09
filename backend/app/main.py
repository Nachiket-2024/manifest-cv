import asyncio
import os
import signal
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import dotenv_values
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Local Python runs use the same two development env files as the Compose
# stack. Process variables still win, so CI/Compose can inject another mode
# without this fallback changing it. App values are loaded last, matching
# Compose's mystic_auth-then-app precedence.
for _key, _value in {
    **dotenv_values(BASE_DIR / "env" / "mystic_auth" / ".env.dev"),
    **dotenv_values(BASE_DIR / "env" / "app" / ".env.dev"),
}.items():
    if _value is not None:
        os.environ.setdefault(_key, _value)

# Every import below must follow the env fallback above, since sdk.py (and
# the ManifestCV route modules that transitively import it) reads env-dependent
# settings at import time. ManifestCV's own domains are mounted the same way
# as every mystic-auth router below (see app/sdk.py and app/app_sdk.py for
# the loose-coupling boundary these route modules use to reach identity/current-user).
from .api.application_routes.application_routes import router as application_router  # noqa: E402
from .api.career_knowledge_routes.career_knowledge_routes import router as career_knowledge_router  # noqa: E402
from .api.resume_builder_routes.job_routes import job_router as resume_job_router  # noqa: E402
from .api.resume_builder_routes.resume_builder_routes import router as resume_builder_router  # noqa: E402
from .app_sdk import register_extensions  # noqa: E402
from .retrieval.qdrant_client import close_client as close_qdrant_client  # noqa: E402
from .retrieval.qdrant_client import ensure_collection as ensure_qdrant_collection  # noqa: E402
from .sdk import (  # noqa: E402
    AppError,
    CorrelationIdMiddleware,
    LoggingMiddleware,
    SecurityHeadersMiddleware,
    auth_router,
    authorization_check_router,
    bulk_permission_router,
    bulk_policy_router,
    bulk_role_router,
    capture_exception,
    database,
    get_logger,
    health_router,
    init_sentry,
    pbac_audit_log_router,
    permission_assignment_router,
    permission_catalog_router,
    policy_assignment_router,
    policy_crud_router,
    policy_history_router,
    policy_self_router,
    procrastinate_app,
    rate_limit_router,
    refresh_token_router,
    security_audit_router,
    settings,
    signal_session_events_shutdown,
    user_lifecycle_router,
    user_management_query_router,
    user_management_update_router,
    user_self_service_router,
    valkey_client,
    watch_for_late_dsn,
)

logger = get_logger("main")

# The app-owned extension hook is a no-op in the template. Downstream projects
# add handlers and other startup registration in backend/app/app_sdk.py
# without editing backend/mystic_auth/.
register_extensions()

# Import configured downstream task modules only after the public SDK has
# finished initializing. A downstream task is allowed to import `app.sdk`;
# loading it from procrastinate_app.py during the SDK import would expose a
# partially initialized module and make the API unhealthy at startup.
procrastinate_app.perform_import_paths()

# Before the app starts serving requests, so every request from the very
# first one onward is covered. A no-op when SENTRY_DSN is unset (see
# error_monitoring/sentry_service.py and docs/mystic_auth/error-monitoring/overview.md).
init_sentry()


def _relay_shutdown_signal_to_session_events() -> None:
    """
    Runs signal_session_events_shutdown() the instant SIGTERM/SIGINT arrives,
    ahead of uvicorn's own handler.

    Why: uvicorn's shutdown waits for every open connection to close on its
    own before it calls our lifespan teardown, with no default timeout. A
    GET /auth/session-events stream never closes by itself, so signaling
    from inside lifespan teardown would never run - uvicorn would already be
    stuck waiting for that same connection forever. Chaining in front of
    uvicorn's handler here (installed at import time, before uvicorn
    registers its own) fires our shutdown signal first, then still calls
    uvicorn's original handler so its own shutdown sequence is unaffected.

    Only works on the main thread; signal.signal() raises off it, so we just
    skip installing the relay in that case.
    """
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            previous_handler = signal.getsignal(sig)
        except ValueError:
            return

        def _handler(signum: int, frame: object, _previous: object = previous_handler) -> None:
            signal_session_events_shutdown()
            if callable(_previous):
                _previous(signum, frame)

        try:
            signal.signal(sig, _handler)
        except ValueError:
            return


_relay_shutdown_signal_to_session_events()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """
    On startup, ensures ManifestCV's Qdrant collection exists (idempotent,
    safe on every restart, see retrieval/qdrant_client.py) and starts
    watch_for_late_dsn() as a fire-and-forget background task, a no-op
    unless init_sentry() above ran with SENTRY_DSN still unset (see that
    function's own docstring: Bugsink can take longer to become healthy
    than this app takes to boot on a fresh/cold start). Never awaited, so
    it can't delay startup or block a single request. Cancelled on
    shutdown along with everything else.

    On shutdown (SIGTERM from `docker stop` / orchestrator rolling
    restarts) explicitly dispose the DB connection pool and close the
    Valkey and Qdrant clients instead of relying on the process dying and
    the OS reclaiming the sockets. Session-events streams are already told
    to stop by _relay_shutdown_signal_to_session_events() before this runs.
    """
    await ensure_qdrant_collection()
    dsn_watcher = asyncio.create_task(watch_for_late_dsn())
    # Opens procrastinate_app's psycopg pool (separate from database.engine's
    # SQLAlchemy pool) so request handlers deferring send_email_task have a
    # live connector from the first request.
    await procrastinate_app.open_async()
    yield
    dsn_watcher.cancel()
    await database.engine.dispose()
    await valkey_client.aclose()
    await close_qdrant_client()
    await procrastinate_app.close_async()


# In production, the interactive API docs are disabled: they're a debugging
# aid with no reason to be publicly reachable, and disabling them is one less
# thing to lock down at a proxy.
_is_production = settings.ENVIRONMENT.lower() == "production"
app = FastAPI(
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
    # Starlette's default trailing-slash redirect builds its Location from
    # request.url, which is always http:// here (nginx proxies to this
    # backend over plain HTTP, and nothing restores the original scheme) -
    # so a client hitting e.g. POST /auth/login/ got redirected to
    # http://..., leaking the request body (credentials) in plaintext if
    # the client actually followed it. No real caller relies on the
    # trailing-slash form, so disabling it entirely (404 instead of a
    # same-method/body redirect) removes the downgrade without needing a
    # trusted-proxy scheme middleware.
    redirect_slashes=False,
)

# Starlette applies middleware in reverse of add order: the LAST one added
# is OUTERMOST, running first. CorrelationIdMiddleware is added last so
# request.state.request_id is populated before every other middleware runs.

# Origins come from settings (FRONTEND_BASE_URL + optional
# FRONTEND_ADDITIONAL_BASE_URLS), not hardcoded, so this works across
# environments. Redirect/email links always point at FRONTEND_BASE_URL
# alone regardless of how many origins are CORS-allowed here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
    # Custom response headers are invisible to browser JS by default;
    # without this, X-Total-Count (see list_all_users) and
    # Content-Disposition (the download filename) are on the wire but
    # unreadable via axios.
    expose_headers=["X-Total-Count", "Content-Disposition"],
)

app.add_middleware(LoggingMiddleware)

# Rejects a request whose Host header doesn't match FRONTEND_BASE_URL/
# FRONTEND_ADDITIONAL_BASE_URLS (plus localhost, for the in-container
# healthcheck and local direct-port debugging - see settings.trusted_hosts).
# nginx and the local-prod tunnels already enforce their own Host
# expectations, but hitting the backend's own localhost-only port directly
# bypassed both with nothing in the app itself checking - this is that
# missing layer, not a replacement for either.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

# Security headers must wrap TrustedHostMiddleware: rejected Host responses
# otherwise return before this middleware gets a chance to add the browser
# hardening headers. See security_headers_middleware.py for per-header
# reasoning.
app.add_middleware(SecurityHeadersMiddleware)

# Added last so it becomes outermost (see note above).
app.add_middleware(CorrelationIdMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    # Same shape as FastAPI's default handler, plus "code"/"params" so the
    # frontend can look up a translated message instead of showing this
    # English `detail` string directly.
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code, "params": exc.params},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    # FastAPI's default 422 body includes each rejected field's raw
    # `input`. That can echo submitted passwords, reset tokens, or bearer
    # material back to clients and logs. Keep location/type/message, drop
    # the original value.
    sanitized_errors = [
        {key: value for key, value in error.items() if key != "input"}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(sanitized_errors)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled Exception at {request.url.path}: {str(exc)}")
    await capture_exception(exc, request=request)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


app.include_router(auth_router)
app.include_router(refresh_token_router)
# Split by operation type across backend/mystic_auth/api/user_routes/.
# Registration order matters: the self-service router must come first, or
# the management routers' PUT /users/{user_email} would shadow PUT
# /users/me (Starlette matches routes in registration order app-wide).
app.include_router(user_self_service_router)
app.include_router(user_management_query_router)
app.include_router(user_management_update_router)
app.include_router(user_lifecycle_router)
# Split by sub-domain across backend/mystic_auth/api/pbac_routes/.
# policy_assignment_router defines /authorization/users/me/policies before
# its own /{user_email}/policies, so it must be included whole; no other
# cross-router ordering constraint exists.
app.include_router(policy_crud_router)
app.include_router(policy_history_router)
app.include_router(policy_self_router)
app.include_router(policy_assignment_router)
app.include_router(permission_assignment_router)
app.include_router(permission_catalog_router)
app.include_router(bulk_policy_router)
app.include_router(bulk_permission_router)
app.include_router(bulk_role_router)
app.include_router(authorization_check_router)
app.include_router(pbac_audit_log_router)
app.include_router(security_audit_router)
app.include_router(rate_limit_router)
app.include_router(health_router)

# ManifestCV's own structured product domains.
app.include_router(career_knowledge_router)
app.include_router(resume_builder_router)
app.include_router(resume_job_router)
app.include_router(application_router)


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}!"}
