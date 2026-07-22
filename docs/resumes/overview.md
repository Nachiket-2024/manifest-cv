# Resumes

Tailored resume drafts, one per job description a user is applying to — unlike the career knowledge base (one row per user), a user has many resume drafts. Backend: `resume_table/`, `resume_crud/`, `api/resume_routes/`. Frontend: `frontend/src/resumes/`.

## The model

`ResumeDraft` (`resume_drafts` table), many per user:

| Column | Purpose |
|---|---|
| `job_description` | The target job posting text |
| `resume_content` | AI-generated (then optionally edited) Markdown resume — `null` until first generation |
| `status` | `"draft"` or `"approved"` — a plain string column, not a DB enum, matching this codebase's preference for permissive status columns over one that needs a migration to extend |

## Flow

1. **Create** (`POST /resumes/`) — the caller supplies a job description. The backend semantically retrieves matching excerpts from the caller's own career knowledge base (`retrieval.knowledge_retrieval_service.search_knowledge_base`, top 8 chunks), then Gemini generates an initial resume from those excerpts alone (`ai_integration.gemini_client.generate_resume`). If the knowledge base has no matching content at all, the request is rejected with `400` — there's nothing to generate from.
2. **Edit** (`PUT /resumes/{id}`) — two paths sharing one endpoint:
   - `content` alone: a direct manual edit, no AI call.
   - `refinement_prompt`: re-matches the knowledge base against `job_description + refinement_prompt`, then Gemini regenerates the resume from the previous content plus the refinement instruction (`ai_integration.gemini_client.refine_resume`) — so asking to "pull in more of my project experience" can actually retrieve different excerpts, not just rephrase the existing text.
   - If both are supplied, `refinement_prompt` wins.
3. **Approve** (`POST /resumes/{id}/approve`) — locks the content. From this point, `PUT` is rejected with `400` ("This resume has been approved and its content is locked") — only template selection and PDF generation (see [Document Generation](../document-generation/overview.md)) may proceed. Approving a draft with no content at all is also rejected.
4. **Delete** (`DELETE /resumes/{id}`) — cascades to any finalized document (`resume_documents.resume_draft_id` has `ondelete="CASCADE"`).

## Ownership and access

No PBAC permission required — every route is scoped to the caller's own `user_id` (see [Auth & Authorization](../auth/overview.md#no-pbac-on-manifestcvs-own-routes)). A draft id belonging to another user 404s.

## Pagination

`GET /resumes/` accepts `limit` (default 20, max 100) and `offset` (default 0) query params, newest-first (`ResumeDraft.created_at.desc()`, with `id.desc()` as a tie-breaker for a fully stable sort when two drafts share a timestamp). Same convention as the inherited audit-log endpoints (`api/audit_log_routes/`). The frontend (`ResumeDraftsPage.tsx`) drives this with a `ui/Pager.tsx` Previous/Next control — a page returning fewer than `limit` rows is treated as the last page, so no separate total-count endpoint is needed.

## Rate limiting

`POST /resumes/` and `PUT /resumes/{id}` are both rate-limited (`auth.security.rate_limiter_service.rate_limited`, keyed per-account by email), same reasoning as [Career Knowledge's rate limiting](../career-knowledge/overview.md#rate-limiting) — both routes can trigger a real Gemini generation/refinement call. `job_description`/`content` are capped at 50,000 characters and `refinement_prompt` at 2,000 (`ResumeDraftCreate`/`Update` schemas) — a refinement is meant to be a short instruction, not another full document.

## Failure modes

Both the retrieval step and the Gemini generation/refinement calls can fail; both surface as `502 Bad Gateway` (`AIIntegrationError` for Gemini, `RetrievalError` for Qdrant — see [AI & Retrieval](../ai-and-retrieval/overview.md)), distinct from the `400` returned when retrieval succeeds but finds nothing relevant to generate from. A Gemini/Qdrant call that hangs rather than erroring is also bounded — see [AI & Retrieval: timeouts](../ai-and-retrieval/overview.md#timeouts).

## API reference

See [API Reference](../api/reference.md) (Resumes section) for the full request/response shapes.
