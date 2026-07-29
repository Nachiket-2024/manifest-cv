"""
App-specific extension surface (see docs/mystic_auth/template-usage/overview.md).

This is the counterpart to sdk.py: sdk.py re-exports the template's own
building blocks, this file is where a project built on this template adds
its own re-exports for its own domain code, kept separate so template
updates never conflict with app-specific additions here.

ManifestCV's own additions:
- get_user_id_by_email: the translation every owner-scoped ManifestCV route
  depends on to turn mystic-auth's get_current_user (email-only) into a DB
  user_id.
- get_logger, rate_limiter_service: sdk.py deliberately doesn't re-export
  these (it's a fixed, upstream-maintained file — see its own docstring),
  so ManifestCV's own route modules that need them import through here
  instead of reaching into mystic_auth.logging/mystic_auth.auth.security
  directly, keeping that boundary in exactly one place.
"""

import importlib

from sqlalchemy.ext.asyncio import AsyncSession

# Same dual-context import trick as sdk.py (see that file's own docstring
# for the full reasoning) — this file is imported as bare `app.app_sdk`
# under Docker/uvicorn (WORKDIR=backend) and as `backend.app.app_sdk` from
# the repo-root test suite, and `mystic_auth` needs to resolve to the exact
# same module identity either way.
_pkg_parent = __package__.rsplit(".", 1)[0] if __package__ and "." in __package__ else ""
_mystic_auth_root = f"{_pkg_parent}.mystic_auth" if _pkg_parent else "mystic_auth"
user_crud = importlib.import_module(f"{_mystic_auth_root}.user_crud.user_crud_collector").user_crud
get_logger = importlib.import_module(f"{_mystic_auth_root}.logging.logging_config").get_logger
rate_limiter_service = importlib.import_module(
    f"{_mystic_auth_root}.auth.security.rate_limiter_service"
).rate_limiter_service


async def get_user_id_by_email(email: str, db: AsyncSession) -> int | None:
    """
    Resolves a user's DB id from their email — the only stable identifier
    mystic-auth's get_current_user dependency exposes (its returned dict
    carries email/role/permissions, never an id). ManifestCV feature tables
    use user_id as their foreign key, so every owner-scoped route needs
    this lookup once per request.
    """
    user = await user_crud.get_by_email(email, db)
    return user.id if user else None
