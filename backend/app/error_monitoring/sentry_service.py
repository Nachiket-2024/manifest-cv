import sentry_sdk
from fastapi import Request

from ..core.settings import settings
from ..auth.token_logic.jwt_service import jwt_service
from ..logging.logging_config import get_startup_logger

# Whether error monitoring is enabled is a one-time, boot-relevant fact
# worth seeing directly in `docker compose logs` — unlike get_logger()'s
# routine INFO logging elsewhere in this app, which is deliberately
# file-only (see get_logger()'s own docstring).
startup_logger = get_startup_logger(__name__)


def init_sentry() -> None:
    """
    Initializes the Sentry SDK if SENTRY_DSN is configured — a complete
    no-op otherwise, so this template behaves identically whether or not
    error monitoring is wired up. Call once at import time, before the app
    starts serving requests (see main.py).

    Works against Sentry itself or any self-hosted server that speaks the
    same protocol (e.g. Bugsink — see docs/error-monitoring/overview.md); nothing
    here is Sentry-the-company-specific beyond the SDK package name.

    Deliberately never lets a bad SENTRY_DSN take the whole app down.
    sentry_sdk.init() raises (e.g. sentry_sdk.utils.BadDsn) on a malformed
    DSN, and this function runs unguarded at import time in main.py, before
    the app's own global_exception_handler exists to catch anything — a
    typo in what's meant to be an optional, best-effort setting would
    otherwise crash startup entirely. Caught broadly (not just BadDsn)
    since any other init-time failure here should degrade the same way:
    error monitoring stays off, the app itself starts regardless.
    """
    if not settings.SENTRY_DSN:
        startup_logger.info("SENTRY_DSN not set — error monitoring disabled.")
        return

    try:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT,
            # This template has no other use for tracing/performance sampling —
            # sending 0% keeps every event an intentional capture_exception()
            # call (below) rather than adding request-tracing overhead nobody
            # asked for. Error capture itself is unaffected by this setting.
            traces_sample_rate=0.0,
            # send_default_pii defaults to False in sentry-sdk — deliberately
            # left at that default rather than overridden to True. User
            # identification is instead attached explicitly and narrowly (just
            # an email, via set_user in capture_exception below), not via the
            # SDK's broader automatic PII collection (request bodies, cookies,
            # etc.), which could otherwise capture credentials in transit.
        )
    except Exception:
        startup_logger.warning(
            "SENTRY_DSN is set but the Sentry SDK failed to initialize — "
            "error monitoring is disabled for this run. Check the DSN value.",
            exc_info=True,
        )
        return

    startup_logger.info(
        "Sentry-protocol error monitoring initialized (environment=%s).",
        settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT,
    )


async def capture_exception(exc: Exception, request: Request | None = None) -> None:
    """
    Reports exc to the configured error-monitoring server. Safe to call
    even when init_sentry() was never invoked (SENTRY_DSN unset) — the SDK
    itself no-ops capture_exception when no client is bound, so callers
    (main.py's global exception handler) don't need their own "is this
    enabled" check.

    Called from the one place every otherwise-unhandled exception already
    passes through (main.py's global_exception_handler) — that handler
    intercepts and converts every exception to a clean generic 500 before
    it would otherwise propagate as "unhandled" from Starlette's own
    perspective, which is also the point sentry-sdk's automatic
    FastAPI/Starlette instrumentation normally hooks into. Without this
    explicit call, that automatic instrumentation would never see anything
    to report, since nothing ever reaches it unhandled.

    Best-effort attaches the caller's email as Sentry user context, read
    directly from the access_token cookie — this fires from the global
    exception handler itself, outside any specific route's own dependency
    chain, so there's no already-resolved current_user available to reuse.
    A cookie that's missing, expired, or otherwise fails to verify simply
    means no user context is attached; it never blocks the capture itself.
    """
    email = await _resolve_caller_email(request) if request is not None else None

    if email:
        sentry_sdk.set_user({"email": email})

    if request is not None:
        sentry_sdk.set_context("request", {"method": request.method, "path": request.url.path})

    sentry_sdk.capture_exception(exc)


async def _resolve_caller_email(request: Request) -> str | None:
    access_token = request.cookies.get("access_token")
    if not access_token:
        return None

    payload = await jwt_service.verify_token(access_token, expected_type="access")
    return payload.get("email") if payload else None
