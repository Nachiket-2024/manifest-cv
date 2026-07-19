# AI & Retrieval

The two pieces that power the AI-assisted parts of career knowledge and resume generation. Backend: `ai_integration/` (Gemini) and `retrieval/` (Qdrant).

## AI integration (`ai_integration/`)

Wraps Google's Gemini API (`google-genai` SDK) behind a small, purpose-specific function set — no generic "call the LLM" abstraction, since every caller has a fixed prompt shape (see `ai_integration/prompts.py`).

| Function | Used by | Purpose |
|---|---|---|
| `structure_knowledge_base(raw_input)` | [Career Knowledge](../career-knowledge/overview.md) | Reorganizes a raw text dump into clean Markdown — rewrite/summarize/reorganize allowed, inventing new facts is not (a prompt-level constraint, not code-enforced) |
| `generate_resume(job_description, knowledge_chunks)` | [Resumes](../resumes/overview.md) | Generates an initial tailored resume from retrieved knowledge base excerpts only |
| `refine_resume(job_description, knowledge_chunks, previous_resume, refinement_prompt)` | [Resumes](../resumes/overview.md) | Regenerates a resume per a refinement instruction, re-matching the knowledge base rather than only editing the previous text verbatim |
| `embed_text(text)` | `retrieval/` | Generates a semantic embedding vector for one chunk of text |

The `genai.Client` is constructed lazily, on first use — importing `ai_integration` never requires a valid `GEMINI_API_KEY`, so the rest of the app (and its tests) can import modules that transitively reference it without needing a real key.

Every text-generation call funnels through one shared `_generate_text` helper: a failure (network error, empty response) raises `AIIntegrationError`, which every route that calls into `ai_integration` catches and turns into `502 Bad Gateway` — a failure of an upstream dependency, never an unhandled `500`.

### Embedding dimensionality

`EMBEDDING_DIMENSIONS = 768`. `gemini-embedding-001` is MRL-trained (Matryoshka Representation Learning), so truncating its native output to a smaller dimensionality via `output_dimensionality` still yields a meaningful vector — unlike naively slicing an untrained model's output, which would not. This value must match Qdrant's collection definition exactly (fixed-size vectors).

### Timeouts

Every outbound Gemini call (`_generate_text`, `embed_text`) is wrapped in `asyncio.wait_for(..., timeout=30)` — without it, a stalled or unusually slow Gemini response would hang the request (and the coroutine serving it) indefinitely rather than failing visibly. A timeout raises `AIIntegrationError` the same as any other Gemini failure, so it surfaces as the usual `502 Bad Gateway` at the route level, not a distinct error path.

## Retrieval (`retrieval/`)

### Qdrant client (`retrieval/qdrant_client.py`)

One shared collection, `career_knowledge_chunks`, for every user's knowledge base chunks — isolated per user via a payload filter (`user_id`), not one Qdrant collection per user (collections are a heavier unit than that, and this scales fine at this data size). `ensure_collection()` creates it idempotently if missing; called once at backend startup (`main.py`'s lifespan), safe on every restart.

### Chunking (`knowledge_retrieval_service.chunk_markdown`)

Splits a knowledge base's Markdown on headings (`#` through `######`), so a search can retrieve one relevant section (e.g. "Skills") instead of the whole document. Falls back to treating the whole document as one chunk if it has no headings at all.

### Indexing (`index_knowledge_base(user_id, content)`)

Re-indexes a user's **entire** knowledge base on every save: deletes every existing point for that user, then embeds and stores the current chunk set. Chosen over diffing old vs. new chunks — a shrinking section count would otherwise leave stale orphaned points behind — and knowledge bases are small enough that full re-embedding on every save is cheap. Point ids are deterministic (`uuid5` of `user_id` + chunk index), so re-indexing overwrites in place rather than accumulating duplicates when the chunk count is unchanged.

### Search (`search_knowledge_base(user_id, query, top_k)`)

Embeds the query, then queries Qdrant filtered to that user's own points only — a query can never return another user's knowledge base content, enforced server-side, not by trusting the caller. Powers both the standalone `GET /career-knowledge/search` endpoint and resume generation/refinement's internal retrieval step.

## Failure modes

Any Gemini or Qdrant failure during structuring, generation, refinement, indexing, or search surfaces as `AIIntegrationError` → `502 Bad Gateway` at the route level. A resume generation request against an empty or non-matching knowledge base is a distinct case — retrieval *succeeds* but finds nothing, which routes treat as `400 Bad Request` ("Your career knowledge base is empty"), not a provider failure.
