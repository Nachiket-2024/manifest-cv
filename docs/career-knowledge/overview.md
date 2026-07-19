# Career Knowledge

One private knowledge base per user — the single source of truth every tailored resume is generated from. Backend: `career_knowledge_table/`, `career_knowledge_crud/`, `api/career_knowledge_routes/`. Frontend: `frontend/src/career_knowledge/`.

## The model

`CareerKnowledgeBase` (`career_knowledge_bases` table) is exactly one row per user (`user_id` is unique, cascades on account deletion):

| Column | Purpose |
|---|---|
| `raw_input` | The text the user pastes in — resume text, LinkedIn export, GitHub projects, notes, achievements, whatever they have |
| `content` | The structured Markdown knowledge base built from `raw_input` |

Kept as one row, not a collection of entries — this is deliberately "the whole picture", not a list of separate notes, since resume generation later retrieves *sections* of it, not separate documents.

## Flow

1. **Bootstrap** (`POST /career-knowledge/`) — the user pastes their raw career dump. Gemini (`ai_integration.gemini_client.structure_knowledge_base`) reorganizes it into clean Markdown: rewrite, summarize, reorganize allowed; inventing anything not present in the input is not (enforced via the prompt, not code — an LLM call can't be made to structurally guarantee this). The result is embedded and indexed into Qdrant (see [AI & Retrieval](../ai-and-retrieval/overview.md)) so it's searchable immediately.
2. **Direct editing** (`PUT /career-knowledge/` with `content`) — the user edits the Markdown by hand, no AI involved. Re-indexed in Qdrant so search stays in sync with what's actually stored.
3. **Re-structuring** (`PUT /career-knowledge/` with `raw_input`) — a fresh raw dump regenerates `content` from scratch via Gemini, same as step 1.
4. **Search** (`GET /career-knowledge/search?query=...&top_k=...`) — semantic search over the caller's own indexed chunks. Scaffolding for resume generation's own retrieval step (see [Resumes](../resumes/overview.md)); exposed as its own endpoint so retrieval correctness can be verified independently.
5. **Delete** (`DELETE /career-knowledge/`) — removes the row and every indexed Qdrant point for the user.

Only one knowledge base per user: a second `POST` while one already exists is a `409 Conflict` — the caller should `PUT` instead.

## Ownership and access

No PBAC permission is required for any of these routes — see [Auth & Authorization](../auth/overview.md#no-pbac-on-manifestcvs-own-routes) for why. Every operation is scoped to the caller's own `user_id`, resolved from their session via `mystic_auth_adapter.get_user_id_by_email`.

## Rate limiting

`POST /career-knowledge/` and `PUT /career-knowledge/` are both rate-limited (`auth.security.rate_limiter_service.rate_limited`, keyed per-account by email) — every call to either can trigger a real Gemini API call, unlike a plain CRUD write, so both share the same protection auth's own expensive endpoints (signup, login) get. `GET`/`DELETE`/`search` are not rate-limited beyond the mechanism's own IP-level default, since they either don't call Gemini (`GET`, `DELETE`) or are a read with its own natural cost ceiling (`search`'s `top_k` is capped at 20). See [Known Issues: one global rate-limit threshold](../concerns/README.md#one-global-rate-limit-threshold-for-every-endpoint) for the current limitation of this (shared, not endpoint-tuned) threshold.

`raw_input`/`content` are also capped at 50,000 characters (`CareerKnowledgeBaseCreate`/`Update` schemas) — generous for a genuinely long text dump, but bounded against an oversized request being sent wholesale into a Gemini prompt.

## Failure modes

A Gemini failure during structuring surfaces as `502 Bad Gateway` (`ai_integration.exceptions.AIIntegrationError`), not a generic `500` — it's an upstream dependency failure, not a bug in this code. The knowledge base row itself is only created/updated after structuring succeeds, so a failed AI call never leaves a half-structured `content` behind. A Gemini call that doesn't respond at all (rather than erroring) is bounded too — see [AI & Retrieval: timeouts](../ai-and-retrieval/overview.md#timeouts).

## API reference

See [API Reference](../api/reference.md#career-knowledge) for the full request/response shapes.
