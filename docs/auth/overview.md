# Auth & Authorization

ManifestCV doesn't implement its own authentication or authorization — it's built on [mystic-auth](https://github.com/Nachiket-2024/mystic-auth), a full-stack identity/PBAC template, vendored into `backend/app/` and `frontend/src/` unmodified. For how login, signup, OAuth2, tokens, PBAC policies, or audit logging actually work, see [mystic-auth's own documentation](https://github.com/Nachiket-2024/mystic-auth/tree/main/docs) — this repo doesn't duplicate it.

What's documented here is the ManifestCV-specific part: how ManifestCV's own product code (resumes, career knowledge, applications, document generation) reaches into that foundation without becoming tightly coupled to it.

## The boundary: `mystic_auth_adapter/`

`backend/app/mystic_auth_adapter/` is the only module ManifestCV's feature code is allowed to import identity logic from. It re-exports exactly two things:

- **`get_current_user`** — a straight re-export of mystic-auth's own `auth.current_user.current_user_dependency.get_current_user` FastAPI dependency. It's not wrapped or reimplemented; every ManifestCV route depends on the exact same dependency mystic-auth's own routes use, so session/cookie/token behavior is identical everywhere.
- **`get_user_id_by_email`** — a small translation function. mystic-auth's `get_current_user` returns a dict (`email`, `role`, `permissions`), never a database id. ManifestCV's own tables (`resume_drafts`, `career_knowledge_bases`, `application_records`) foreign-key on `user_id`, so every owner-scoped route resolves the caller's id once per request via this function (`user_crud.get_by_email(email, db).id`).

No ManifestCV route imports `..auth.current_user`, `..authorization`, or `..user_crud` directly — only `..mystic_auth_adapter` for *identity resolution*. Two things are imported directly instead, deliberately excluded from the adapter because neither is identity logic: shared infrastructure (`..database.connection`, `..database.base`, `..core.settings`), and `..auth.security.rate_limiter_service` — a generic per-account/per-IP rate limiter, used by `career_knowledge_routes.py`/`resume_routes.py` to throttle their AI-triggering routes (see [Career Knowledge: rate limiting](../career-knowledge/overview.md#rate-limiting)). Routing a cross-cutting utility like rate limiting through an "identity adapter" would conflate two unrelated concerns for no real benefit — the adapter's job is narrowly "who is the caller and what's their DB id," not "every mystic-auth import goes through here."

```python
# The pattern every ManifestCV route follows:
from ...mystic_auth_adapter import get_current_user, get_user_id_by_email

@router.get("/")
async def list_my_resume_drafts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await get_user_id_by_email(current_user["email"], db)
    ...
```

## Why loose, not tight

This mirrors mystic-auth's own guidance for downstream products (see its `docs/template-usage.md`, "Adding your own domain/resource" and "Protecting a new route"): a product built on the template owns its own top-level packages and mounts its own routers, without reaching into the template's internals beyond one narrow, well-defined dependency surface. Concretely, that buys two things:

1. **Upgrading mystic-auth stays cheap.** When the vendored code is refreshed from upstream, only `mystic_auth_adapter/`'s two files need to be checked against the new `current_user_dependency`/`user_crud` shape — not every route module across `career_knowledge_*`, `resume_*`, `application_*`, and `document_generation`.
2. **No mystic-auth code is ever edited to fit ManifestCV.** Every customization ManifestCV needs (routers mounted in `main.py`, settings appended in `core/settings.py`, cache-clearing behavior, etc.) lives in files ManifestCV owns or in narrow, clearly-marked additions to shared files — never inside mystic-auth's own `auth/`, `authorization/`, `user_crud/`, or `user_table/` modules.

## No PBAC on ManifestCV's own routes

mystic-auth's routes are gated by `require_authorization(action, resource_type)` — Policy-Based Access Control. ManifestCV's own routes (career knowledge, resumes, applications, documents) deliberately don't use it: these are self-service, private-per-user resources (a user's own knowledge base, their own resume drafts), not resources where *who else* can act on *whose* data needs a policy decision. Ownership is enforced the simpler way — every query is scoped by the caller's own `user_id`, resolved via `get_user_id_by_email` above, so a caller-supplied id belonging to another user 404s rather than ever being reachable. This is the same reasoning mystic-auth itself applies to its own self-service routes (e.g. `GET /audit/security-log/me`).

## The frontend mirrors this

`frontend/src/career_knowledge/`, `resumes/`, and `applications/` never import from `auth/`, `authorization/`, or `store/authStore` directly — they only use shared, non-identity infrastructure (`store/queryClient`, `api/apiError`, `core/settings`, `components/ui/*`). Session state (is the user logged in at all) is handled once, at the app root, by mystic-auth's own `useAuthSession`/`ProtectedRoute` — ManifestCV's routes are wrapped in the same `ProtectedRoute` as everything else, just without a `permission` prop.
