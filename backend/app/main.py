from dotenv import load_dotenv
from pathlib import Path

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_ = load_dotenv(dotenv_path=BASE_DIR / ".env")

from .core.settings import settings

from .api.auth_routes.auth_routes import router as auth_router
from .api.auth_routes.refresh_token_routes import router as refresh_token_router
from .api.user_routes.user_routes import router as user_router
from .api.pbac_routes.policy_crud_routes import router as policy_crud_router
from .api.pbac_routes.policy_history_routes import router as policy_history_router
from .api.pbac_routes.policy_assignment_routes import router as policy_assignment_router
from .api.pbac_routes.authorization_check_routes import router as authorization_check_router
from .api.pbac_routes.pbac_audit_log_routes import router as pbac_audit_log_router
from .api.audit_log_routes.audit_log_routes import router as security_audit_router
from .api.health_routes.health_routes import router as health_router

# ManifestCV's own domains — mounted the same way as every mystic-auth
# router above (see app/sdk.py and app/manifestcv_sdk.py for the loose-coupling
# boundary these route modules use to reach identity/current-user).
from .api.career_knowledge_routes.career_knowledge_routes import router as career_knowledge_router
from .api.resume_routes.resume_routes import router as resume_router
from .api.document_routes.document_routes import router as document_router
from .api.application_routes.application_routes import router as application_router

# Database engine and Redis client singletons, closed on shutdown below.
from .database.connection import database
from .redis.client import redis_client
from .retrieval.qdrant_client import ensure_collection as ensure_qdrant_collection, close_client as close_qdrant_client

from .logging.logging_middleware import LoggingMiddleware
from .logging.correlation_id_middleware import CorrelationIdMiddleware
from .auth.security.security_headers_middleware import SecurityHeadersMiddleware
from .logging.logging_config import get_logger

from .error_monitoring.sentry_service import init_sentry, capture_exception

logger = get_logger("main")

# Before the app starts serving requests — so every request from the very
# first one onward is covered. A no-op when SENTRY_DSN is unset (see
# error_monitoring/sentry_service.py and docs/error-monitoring/overview.md).
init_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """
    On startup, ensures ManifestCV's Qdrant collection exists (idempotent —
    safe on every restart, see retrieval/qdrant_client.py). On shutdown
    (SIGTERM from `docker stop` / orchestrator rolling restarts) explicitly
    dispose the DB connection pool and close the Redis and Qdrant clients
    instead of relying on the process dying and the OS reclaiming the
    sockets.
    """
    await ensure_qdrant_collection()
    yield
    await database.engine.dispose()
    await redis_client.aclose()
    await close_qdrant_client()


# In production, the interactive API docs are disabled — they're a debugging
# aid with no reason to be publicly reachable, and disabling them is one less
# thing to lock down at a proxy.
_is_production = settings.ENVIRONMENT.lower() == "production"
app = FastAPI(
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# Starlette applies middleware in reverse of add order — the LAST middleware
# added ends up OUTERMOST, running first on the way in. So
# CorrelationIdMiddleware is added last, making it outermost, so
# request.state.request_id (and the logging contextvar it sets) is populated
# before every other middleware runs, including LoggingMiddleware's "Incoming
# request" log line below.

# Sourced from settings (FRONTEND_BASE_URL) rather than hardcoded, so this
# works unchanged across local/staging/production instead of only ever
# allowing http://localhost:5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_BASE_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

app.add_middleware(LoggingMiddleware)

# Security-hardening response headers (X-Frame-Options, CSP, HSTS, etc.) — see
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
# (CRUD, history, assignment, checks, audit log) — see backend/app/api/pbac_routes/.
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
