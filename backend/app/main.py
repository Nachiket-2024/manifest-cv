import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_ = load_dotenv(dotenv_path=BASE_DIR / ".env")

# Every import below must follow load_dotenv() above, since sdk.py (and the
# ManifestCV route modules that transitively import it) reads env-dependent
# settings at import time. ManifestCV's own domains are mounted the same way
# as every mystic-auth router below (see app/sdk.py and app/app_sdk.py for
# the loose-coupling boundary these route modules use to reach identity/current-user).
from .api.application_routes.application_routes import router as application_router  # noqa: E402
from .api.career_knowledge_routes.career_knowledge_routes import router as career_knowledge_router  # noqa: E402
from .api.document_routes.document_routes import router as document_router  # noqa: E402
from .api.resume_routes.resume_routes import router as resume_router  # noqa: E402
from .retrieval.qdrant_client import close_client as close_qdrant_client  # noqa: E402
from .retrieval.qdrant_client import ensure_collection as ensure_qdrant_collection  # noqa: E402
from .sdk import (  # noqa: E402
    CorrelationIdMiddleware,
    LoggingMiddleware,
    SecurityHeadersMiddleware,
    auth_router,
    authorization_check_router,
    capture_exception,
    database,
    get_logger,
    health_router,
    init_sentry,
    pbac_audit_log_router,
    policy_assignment_router,
    policy_crud_router,
    policy_history_router,
    redis_client,
    refresh_token_router,
    security_audit_router,
    settings,
    user_router,
    watch_for_late_dsn,
)

logger = get_logger("main")

# Before the app starts serving requests, so every request from the very
# first one onward is covered. A no-op when SENTRY_DSN is unset (see
# error_monitoring/sentry_service.py and docs/mystic_auth/error-monitoring/overview.md).
init_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """
    On startup, ensures ManifestCV's Qdrant collection exists (idempotent —
    safe on every restart, see retrieval/qdrant_client.py) and starts
    watch_for_late_dsn() as a fire-and-forget background task, a no-op
    unless init_sentry() above ran with SENTRY_DSN still unset (see that
    function's own docstring for why: Bugsink can take longer to become
    healthy than this app takes to boot, on a fresh/cold start). Never
    awaited, so it can't delay startup or block a single request; cancelled
    on shutdown along with everything else.

    On shutdown (SIGTERM from `docker stop` / orchestrator rolling
    restarts) explicitly dispose the DB connection pool and close the
    Redis and Qdrant clients instead of relying on the process dying and
    the OS reclaiming the sockets.
    """
    await ensure_qdrant_collection()
    dsn_watcher = asyncio.create_task(watch_for_late_dsn())
    yield
    dsn_watcher.cancel()
    await database.engine.dispose()
    await redis_client.aclose()
    await close_qdrant_client()


# In production, the interactive API docs are disabled: they're a debugging
# aid with no reason to be publicly reachable, and disabling them is one less
# thing to lock down at a proxy.
_is_production = settings.ENVIRONMENT.lower() == "production"
app = FastAPI(
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# Starlette applies middleware in reverse of add order: the LAST middleware
# added ends up OUTERMOST, running first on the way in. So
# CorrelationIdMiddleware is added last, making it outermost, so
# request.state.request_id (and the logging contextvar it sets) is populated
# before every other middleware runs, including LoggingMiddleware's "Incoming
# request" log line below.

# Sourced from settings (FRONTEND_BASE_URL + optional
# FRONTEND_ADDITIONAL_BASE_URLS) rather than hardcoded, so this works
# unchanged across local/staging/production instead of only ever allowing
# http://localhost:5173. See Settings.cors_allowed_origins for how the list
# is built. Redirect/email links still always point at FRONTEND_BASE_URL
# alone regardless of how many origins are CORS-allowed here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

app.add_middleware(LoggingMiddleware)

# Security-hardening response headers (X-Frame-Options, CSP, HSTS, etc.), see
# security_headers_middleware.py for per-header reasoning.
app.add_middleware(SecurityHeadersMiddleware)

# Added last so it becomes outermost (see note above).
app.add_middleware(CorrelationIdMiddleware)


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
app.include_router(user_router)
# Split from a single pbac_routes/policy_routes.py into feature-based modules
# (CRUD, history, assignment, checks, audit log), see backend/mystic_auth/api/pbac_routes/.
# Registration order matters: policy_assignment_router defines
# /authorization/users/me/policies before its own
# /authorization/users/{user_email}/policies, so it must be included whole;
# no other cross-router ordering constraint exists since each router owns a
# disjoint set of paths.
app.include_router(policy_crud_router)
app.include_router(policy_history_router)
app.include_router(policy_assignment_router)
app.include_router(authorization_check_router)
app.include_router(pbac_audit_log_router)
app.include_router(security_audit_router)
app.include_router(health_router)

# ManifestCV's own domains. resume_router is included before document_router
# since document_router's prefix ("/resumes/{draft_id}") nests under it.
app.include_router(career_knowledge_router)
app.include_router(resume_router)
app.include_router(document_router)
app.include_router(application_router)


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}!"}
