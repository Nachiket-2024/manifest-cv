# Auth & Authorization

ManifestCV doesn't implement its own authentication or authorization — it's built on [mystic-auth](https://github.com/Nachiket-2024/mystic-auth), a full-stack identity/PBAC template, vendored into `backend/app/` and `frontend/src/` unmodified. For how login, signup, OAuth2, tokens, PBAC policies, or audit logging actually work, see the [Foundation (mystic-auth)](../README.md#foundation-mystic-auth) section of the docs index — copied in locally from upstream, confirmed byte-identical as of this review — starting with [Authentication Overview](../authentication/overview.md) and [PBAC Architecture](../authorization/architecture.md).

What's documented here is the ManifestCV-specific part: how ManifestCV's own product code (resumes, career knowledge, applications, document generation) reaches into that foundation without becoming tightly coupled to it.

## The boundary: `app/sdk.py` + `app/manifestcv_sdk.py`

mystic-auth ships its own public extension surface for downstream code — `backend/app/sdk.py` (see its `docs/template-usage.md#the-extension-surface-sdkpy--sdkts`). ManifestCV's feature code imports identity logic from exactly two places, neither of which reaches into mystic-auth's internals directly:

- **`get_current_user`** — imported straight from `app.sdk`, which re-exports `auth.current_user.current_user_dependency.get_current_user` unchanged. Every ManifestCV route depends on the exact same dependency mystic-auth's own routes use, so session/cookie/token behavior is identical everywhere. Sourcing through `sdk.py` rather than mystic-auth's internal path directly means an upstream rename only ever needs fixing in one file — one mystic-auth already owns and keeps stable — not every ManifestCV route module.
- **`get_user_id_by_email`** — a small translation function ManifestCV owns itself, in `backend/app/manifestcv_sdk.py` (not part of mystic-auth's template; there's nothing to reconcile against upstream here). mystic-auth's `get_current_user` returns a dict (`email`, `role`, `permissions`), never a database id. ManifestCV's own tables (`resume_drafts`, `career_knowledge_bases`, `application_records`) foreign-key on `user_id`, so every owner-scoped route resolves the caller's id once per request via this function (`user_crud.get_by_email(email, db).id`).

No ManifestCV route imports `..auth.current_user`, `..authorization`, `..user_crud`, `..auth.security`, or `..logging` directly — only `..sdk` (`get_current_user`, `database`, `get_or_404`, `settings`, `capture_exception`, `get_logger`, `rate_limiter_service` — every one of these is a straight re-export, so ManifestCV's routes take them from `app.sdk` rather than from `..database.connection`/`..api.route_helpers`/`..core.settings`/`..logging.logging_config`/`..auth.security.rate_limiter_service` directly), and `..manifestcv_sdk` for id resolution. Exactly one thing is imported directly instead of through either SDK: `..database.base` (the declarative `Base` every ManifestCV table model subclasses). This mirrors mystic-auth's own internal modules, which import `Base` the same direct way (e.g. `user_table/user_model.py`) — `sdk.py`'s own `database` export is the session/connection object, not the ORM base class, and a template's own model files were never expected to route through its extension surface for this. `get_logger` and `rate_limiter_service` are both generic, non-identity infrastructure ManifestCV's own routes need (`career_knowledge_routes.py`/`resume_routes.py` use `rate_limiter_service` to throttle their AI-triggering routes — see [Career Knowledge: rate limiting](../career-knowledge/overview.md#rate-limiting)) — both are re-exported by `sdk.py` precisely so reaching for them doesn't mean reaching into mystic-auth's internal module paths.

```python
# The pattern every ManifestCV route follows:
from ...sdk import get_current_user, database, get_or_404
from ...manifestcv_sdk import get_user_id_by_email

@router.get("/")
async def list_my_resume_drafts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await get_user_id_by_email(current_user["email"], db)
    ...
```

## Why loose, not tight

This mirrors mystic-auth's own guidance for downstream products (see its `docs/template-usage.md`, "Adding your own domain/resource" and "Protecting a new route"): a product built on the template owns its own top-level packages and mounts its own routers, importing only from the template's documented extension surface (`app.sdk` / `sdk.ts`) rather than its internals. Concretely, that buys two things:

1. **Upgrading mystic-auth stays cheap.** When the vendored code is refreshed from upstream, only `sdk.py` needs to be reconciled against the new internal shape (mystic-auth's own stated design goal for that file) — not every route module across `career_knowledge_*`, `resume_*`, `application_*`, and `document_generation`. `manifestcv_sdk.py` never needs touching for an upstream update at all — it's ManifestCV's own code, not a translation layer over mystic-auth internals.
2. **No mystic-auth code is ever edited to fit ManifestCV.** Every customization ManifestCV needs (routers mounted in `main.py`, settings appended in `core/settings.py`, cache-clearing behavior, etc.) lives in files ManifestCV owns or in narrow, clearly-marked additions to shared files — never inside mystic-auth's own `auth/`, `authorization/`, `user_crud/`, or `user_table/` modules.

## No PBAC on ManifestCV's own routes

mystic-auth's routes are gated by `require_authorization(action, resource_type)` — Policy-Based Access Control. ManifestCV's own routes (career knowledge, resumes, applications, documents) deliberately don't use it: these are self-service, private-per-user resources (a user's own knowledge base, their own resume drafts), not resources where *who else* can act on *whose* data needs a policy decision. Ownership is enforced the simpler way — every query is scoped by the caller's own `user_id`, resolved via `get_user_id_by_email` above, so a caller-supplied id belonging to another user 404s rather than ever being reachable. This is the same reasoning mystic-auth itself applies to its own self-service routes (e.g. `GET /audit/security-log/me`).

## The frontend mirrors this

`frontend/src/career_knowledge/`, `resumes/`, and `applications/` never import from `auth/`, `authorization/`, `store/authStore`, or `api/axiosInstance`/`api/apiError` directly — they import shared, non-identity infrastructure (`api`, `queryClient`, `extractApiErrorMessage`, `settings`) from `frontend/src/sdk.ts`, mystic-auth's own extension surface for downstream code, plus its own `ui/*` primitives directly (generic UI components with no identity concept). ManifestCV's own API client modules (`api/application_api.ts`, `resume_api.ts`, `career_knowledge_api.ts`, `document_api.ts`) take the shared axios `api` instance the same way, from `../sdk`, not `./axiosInstance` directly. Session state (is the user logged in at all) is handled once, at the app root, by mystic-auth's own `useAuthSession`/`ProtectedRoute` — ManifestCV's routes are wrapped in the same `ProtectedRoute` (imported from `sdk.ts`) as everything else, just without a `permission` prop.
