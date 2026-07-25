# Document Generation

Compiles an approved resume draft into a styled PDF. Backend: `resume_document_table/`, `resume_document_crud/`, `document_generation/`, `api/document_routes/` (nested under `/resumes/{draft_id}`, since document generation always operates on one specific draft). Frontend: part of `frontend/src/app/resumes/` (the finalize/download flow in `ResumeEditorPage.tsx`).

## Pipeline

```
resume_content (Markdown)
  → markdown_to_latex.markdown_to_latex_body()   — converts Markdown to a LaTeX body fragment
  → templates.render_latex_document(template_id, body)  — wraps the body in a template's preamble
  → tectonic_compiler.compile_latex_to_pdf()     — compiles the .tex source to PDF bytes
```

`document_generation/resume_pdf_service.render_resume_pdf(resume_content, template_id)` chains all three steps and returns `(tex_source, pdf_bytes)`.

## Templates

`document_generation/templates.py` defines a small, fixed dict of visual styles (currently `classic`, `modern`) — each is a different LaTeX preamble (fonts, spacing, color accents) wrapped around the *same* converted body. Adding a new visual style means adding one entry here; the Markdown→LaTeX body conversion never needs to change.

## Compilation

`document_generation/tectonic_compiler.py` shells out to [`tectonic`](https://tectonic-typesetting.github.io/), a self-contained LaTeX engine installed as a static binary in the backend Docker image (see [Docker Overview](../docker/overview.md)) — not a full TeX Live install (several GB). Each compilation runs in an isolated temp directory so concurrent requests never collide. A non-zero exit or a missing output PDF raises `LatexCompilationError`, which routes translate to `502 Bad Gateway`.

Bounded by a 60-second `asyncio.wait_for` around the subprocess — tectonic's first-ever compile in a fresh container fetches its LaTeX format bundle over the network, and without a timeout a stalled fetch (or a pathological `.tex` input) would hang the request indefinitely instead of failing with `502`. On timeout the subprocess is killed rather than left running.

## The model

`ResumeDocument` (`resume_documents` table) — one row per draft (`resume_draft_id` is unique). Re-finalizing with a different template **overwrites** the row (`resume_document_repository.upsert`) rather than accumulating history: only the current template selection matters until the user saves an application, at which point `ApplicationRecord` copies an independent snapshot that outlives this row (see [Applications](../applications/overview.md)).

| Column | Purpose |
|---|---|
| `template_id` | Which visual style was used |
| `tex_source` | The compiled LaTeX source (kept for debugging/re-compilation, not re-served) |
| `pdf_bytes` | The compiled PDF |

## Flow

All three routes require the draft to be **approved** first (`resume_drafts.status == "approved"`) — content is locked from that point on, so it's safe to compile.

1. **List templates** (`GET /resumes/{draft_id}/templates`) — static catalog, no compilation.
2. **Preview** (`GET /resumes/{draft_id}/templates/{template_id}/preview`) — compiles on the fly and returns the PDF directly, without persisting anything, so the user can compare styles before committing. Rendered by the frontend in an `<iframe>` (`ResumeEditorPage.tsx`) — but since the frontend and backend are different origins, and mystic-auth's `security_headers_middleware.py` sends `X-Frame-Options: DENY` unconditionally on every response with no per-route carve-out (see [Security Hardening](../../mystic_auth/security/hardening.md)), a direct `<iframe src>` pointing at this route's own URL would render blank. Instead, `document_api.ts`'s `fetchResumeTemplatePreviewBlob` fetches the PDF bytes via axios (cookies still travel, same as every other call) and hands the `<iframe>` a `blob:` object URL created from the response — `X-Frame-Options` only governs framing of the original HTTP resource, not a same-origin blob URL derived from it, so this sidesteps the header entirely without touching mystic-auth's own middleware.
3. **Finalize** (`POST /resumes/{draft_id}/finalize`) — compiles and persists. This is the version `POST /applications` later snapshots.
4. **Fetch metadata** (`GET /resumes/{draft_id}/finalize`) / **Download** (`GET /resumes/{draft_id}/finalize/download`) — the persisted document's metadata or raw PDF bytes.

## Ownership and access

No PBAC permission required — scoped to the caller's own draft (see [Auth & Authorization](../auth/overview.md#no-pbac-on-manifestcvs-own-routes)).

## Testing

Most of `test_document_routes_integration.py` mocks `render_resume_pdf` (fast, deterministic — verifies the approval gate/ownership/persistence around compilation, not compilation itself). Two tests deliberately don't: `test_real_tectonic_finalize_produces_a_valid_pdf` (parametrized over both templates) and `test_real_tectonic_preview_compiles_without_persisting` exercise the real `markdown_to_latex` → `templates` → `tectonic_compiler` pipeline end to end against realistic resume content containing LaTeX-special characters (`%`, `&`, `#`, `$`, `_`, `{`, `}`) — exactly the class of bug (a markdown_to_latex escaping regression, or a broken template preamble) a mocked `render_resume_pdf` can't catch. Skipped automatically wherever the `tectonic` binary isn't on `PATH` (`shutil.which("tectonic")`) — i.e. everywhere except a container built from `docker/backend.Dockerfile` — and run for real in CI's dedicated `real-tectonic` job, which builds that image and runs them inside it (see [CI/CD Overview](../cicd/overview.md)).

## API reference

See [API Reference](../api/reference.md) (Document Generation section) for the full request/response shapes.
