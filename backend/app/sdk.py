"""
Public extension surface for domain/feature code built on top of this
template (see docs/template-usage.md).

Import from HERE, not internal paths like
`app.authorization.dependencies.authorization_dependency` directly — one
file to discover what's available, and one file to reconcile when pulling
in upstream template updates instead of every call site.

Everything below is a straight re-export; see the original module's
docstring for the "why" behind any given piece.
"""

from .authorization.permissions import Permission
from .authorization.dependencies.authorization_dependency import require_authorization
from .authorization.services.authorization_service import authorization_service
from .authorization.context.request_context_builder import build_authorization_context

from .auth.current_user.current_user_dependency import get_current_user

from .database.connection import database
from .core.settings import settings

from .api.route_helpers import get_or_404

from .user_table.user_model import UserRole

from .error_monitoring.sentry_service import capture_exception

from .logging.logging_config import get_logger

from .auth.security.rate_limiter_service import rate_limiter_service

__all__ = [
    # PBAC — see docs/authorization/architecture.md
    "Permission",
    "require_authorization",
    "authorization_service",
    "build_authorization_context",
    # Authentication — see docs/authentication/overview.md
    "get_current_user",
    # Database — Depends(database.get_session) in a route signature
    "database",
    # Settings — add your own fields to Settings in core/settings.py,
    # read them from here rather than os.environ directly
    "settings",
    # Small route helpers
    "get_or_404",
    # Display/grouping metadata only — never a gating decision, see
    # docs/security/decisions.md#role-is-never-used-to-decide-access
    "UserRole",
    # Error monitoring — reports a caught-but-still-noteworthy exception the
    # same way an unhandled one gets reported automatically. A safe no-op
    # when SENTRY_DSN is unset, see docs/error-monitoring/overview.md
    "capture_exception",
    # Structured, correlation-ID-aware logging — get_logger(__name__) in
    # your own module, same as every internal module of this template does.
    "get_logger",
    # Generic Redis-backed request-rate limiter, independent of the
    # login-lockout feature it was originally built for — usable as
    # rate_limiter_service.rate_limited(...) (a decorator) or
    # rate_limiter_service.record_request(key) directly for any endpoint
    # that needs a max-requests-per-window guard (e.g. ManifestCV's own
    # AI-generation routes, see resume_routes.py/career_knowledge_routes.py).
    "rate_limiter_service",
]
