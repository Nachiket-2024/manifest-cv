# API Reference

Full route inventory for ManifestCV's own routes, grouped by `APIRouter` module under `backend/app/api/`. All routers are mounted in `backend/app/main.py`. Interactive docs (`/docs`, `/redoc`, `/openapi.json`) are available whenever `ENVIRONMENT != "production"`.

Every request/response body is a Pydantic schema (`*_schema.py` beside each feature); FastAPI validates the body and returns `422` with a field-by-field error list on a bad payload — no route does its own manual validation.

## Conventions

- **Auth requirement** `session` means "a valid `access_token` cookie, no specific permission" (`Depends(get_current_user)`, imported from mystic-auth's `mystic_auth.sdk` — see [Auth & Authorization](../auth/overview.md)). None of ManifestCV's own routes use PBAC (`permission:action`) — every one is `session` + server-side `user_id` scoping.
- All cookies are httpOnly; the API is never called with a bearer token/header.
- **Rate limited** (marked below) routes are gated by `auth.security.rate_limiter_service.rate_limited(...)`, keyed per-account — see each route's own feature doc for why.

## Inherited from mystic-auth

`/auth/*`, `/auth/refresh/`, `/users/*`, `/authorization/*`, `/audit/*`, `/health/*` are mystic-auth's own routes, vendored unmodified. See [mystic-auth's own API reference](https://github.com/Nachiket-2024/mystic-auth/blob/main/docs/api/reference.md) for the full, permission-annotated inventory.

## Career Knowledge — `/career-knowledge` (`api/career_knowledge_routes/career_knowledge_routes.py`)

See [Career Knowledge](../career-knowledge/overview.md) for the full flow.

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/career-knowledge/` | session, **rate limited** | Structures `raw_input` via Gemini, indexes in Qdrant. `409` if one already exists |
| GET | `/career-knowledge/` | session | `404` if none exists yet |
| PUT | `/career-knowledge/` | session, **rate limited** | `raw_input` re-structures via AI; `content` alone is a direct edit |
| DELETE | `/career-knowledge/` | session | Also removes the user's indexed Qdrant points |
| GET | `/career-knowledge/search?query=&top_k=` | session | Semantic search over the caller's own indexed chunks (`top_k` 1–20, default 5) |

## Resumes — `/resumes` (`api/resume_routes/resume_routes.py`)

See [Resumes](../resumes/overview.md) for the full flow.

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/resumes/` | session, **rate limited** | Retrieves matching knowledge base excerpts, generates via Gemini. `400` if the knowledge base has no matching content |
| GET | `/resumes/?limit=&offset=` | session | Caller's own drafts, newest first, paginated (`limit` 1–100, default 20; `offset` default 0) — see [Resumes: pagination](../resumes/overview.md#pagination) |
| GET | `/resumes/{draft_id}` | session | `404` if not found or not owned by the caller |
| PUT | `/resumes/{draft_id}` | session, **rate limited** | `refinement_prompt` re-matches + regenerates via AI; `content` alone is a direct edit. `400` if the draft is already approved |
| POST | `/resumes/{draft_id}/approve` | session | Locks content. `400` if there's no content to approve |
| DELETE | `/resumes/{draft_id}` | session | Cascades to any finalized document |

## Document Generation — nested under `/resumes/{draft_id}` (`api/document_routes/document_routes.py`)

See [Document Generation](../document-generation/overview.md) for the full pipeline. Every route below requires the draft to be **approved** first (`400` otherwise).

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/resumes/{draft_id}/templates` | session | Static catalog, no compilation |
| GET | `/resumes/{draft_id}/templates/{template_id}/preview` | session | Compiles on the fly, returns PDF directly — nothing persisted |
| POST | `/resumes/{draft_id}/finalize` | session | Compiles and persists — overwrites any previous finalization for this draft |
| GET | `/resumes/{draft_id}/finalize` | session | Persisted document metadata. `404` if not yet finalized |
| GET | `/resumes/{draft_id}/finalize/download` | session | Raw PDF bytes as an attachment |

## Applications — `/applications` (`api/application_routes/application_routes.py`)

See [Applications](../applications/overview.md) for the full flow.

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/applications/` | session | Snapshots the finalized resume for `resume_draft_id`. `400` if that draft has no finalized document yet |
| GET | `/applications/?limit=&offset=` | session | Summary schema (excludes the resume/PDF snapshot), newest first, paginated (`limit` 1–100, default 20; `offset` default 0) — see [Applications: pagination](../applications/overview.md#pagination) |
| GET | `/applications/{application_id}` | session | Full schema — includes the Markdown snapshot |
| GET | `/applications/{application_id}/pdf` | session | Raw PDF snapshot bytes as an attachment |
| PATCH | `/applications/{application_id}` | session | Tracking fields only (company/date/time/status) — the resume snapshot is read-only |
| DELETE | `/applications/{application_id}` | session | |

## Error responses

Every route shares one global exception handler (`main.py`'s `@app.exception_handler(Exception)`): any unhandled exception is logged with a stack trace and returned as a generic `500 {"detail": "Internal Server Error"}` — no internal exception detail ever reaches the client. Expected failures use FastAPI's normal `HTTPException` mechanism (`400`/`401`/`404`/`409`/`422`) with a specific `detail` message per case. ManifestCV's AI-backed routes additionally return `502 Bad Gateway` when Gemini (`AIIntegrationError`) or Qdrant (`RetrievalError`) fails on a call the request can't proceed without (structuring/generation/refinement/search) — indexing/deletion failures after a successful save are handled differently (best-effort, never surfaced as an error) — see [AI & Retrieval](../ai-and-retrieval/overview.md#failure-modes).
