"""
The only door ManifestCV's own feature code (application_*, career_knowledge_*,
resume_*, document_generation, ai_integration, retrieval) is allowed to use into
mystic-auth's identity system. Per mystic-auth's docs/template-usage.md, a
downstream product built on the template owns its own top-level packages and
mounts its own routers — it never needs to reach into auth/authorization/
user_crud internals directly.

Feature code must import `get_current_user` / `get_user_id_by_email` from here,
never reach into `..auth.current_user`, `..authorization`, or `..user_crud`
directly. Keeping the boundary in one place means an upstream mystic-auth
update to *identity resolution* only ever requires fixing these two files,
not every route module across the ManifestCV domains.

Not everything under `..auth`/mystic-auth is identity logic, though, and two
things ARE imported directly by feature code rather than through here:
`..database.connection` / `..database.base` (shared infrastructure with no
identity concept at all), and `..auth.security.rate_limiter_service` (a
generic per-account/per-IP rate limiter, unrelated to who the caller is —
career_knowledge_routes.py/resume_routes.py use it to throttle their
AI-triggering routes). Routing either through this adapter would conflate
identity translation with unrelated infrastructure concerns for no benefit.
"""

from .current_user import get_current_user
from .user_lookup import get_user_id_by_email

__all__ = ["get_current_user", "get_user_id_by_email"]
