# Document Generation

Compiles an approved resume draft into a styled PDF. Backend: `resume_document_table/`, `resume_document_crud/`, `document_generation/`, `api/document_routes/` (nested under `/resumes/{draft_id}`, since document generation always operates on one specific draft). Frontend: part of `frontend/src/app/resumes/` (the finalize/download flow in `ResumeEditorPage.tsx`).

---

## Pipeline

```text
resume_content (Markdown)
  to markdown_to_latex.markdown_to_latex_body()        converts Markdown to a LaTeX body fragment
  to templates.render_latex_document(template_id, body) wraps the body in a template's preamble
  to tectonic_compiler.compile_latex_to_pdf()           compiles the .tex source to PDF bytes
```

`document_generation/resume_pdf_service.render_resume_pdf(resume_content, template_id)` chains all three steps and returns `(tex_source, pdf_bytes)`.

---

## Templates

`document_generation/templates.py` defines a small, fixed dict of visual styles (currently `classic`, `modern`). Each is a different LaTeX preamble (fonts, spacing, color accents) wrapped around the same converted body. Adding a new visual style means adding one entry here. The Markdown to LaTeX body conversion never needs to change.

---

## Compilation

`document_generation/tectonic_compiler.py` shells out to [`tectonic`](https://tectonic-typesetting.github.io/), a self-contained LaTeX engine installed as a static binary in the backend Docker image (see [Docker Overview](../docker/overview.md)). This is not a full TeX Live install. Each compilation runs in an isolated temp directory so concurrent requests never collide. A non-zero exit or a missing output PDF raises `LatexCompilationError`, which routes translate to `502 Bad Gateway`.

Compilation is bounded by a 60-second `asyncio.wait_for` around the subprocess. Tectonic's first compile in a fresh container fetches its LaTeX format bundle over the network, and without a timeout a stalled fetch or pathological `.tex` input would hang the request indefinitely. On timeout the subprocess is killed.

---

## The Model

`ResumeDocument` (`resume_documents` table). One row per draft (`resume_draft_id` is unique). Re-finalizing with a different template overwrites the row (`resume_document_repository.upsert`) rather than accumulating history. Only the current template selection matters until the user saves an application, at which point `ApplicationRecord` copies an independent snapshot that outlives this row (see [Applications](../applications/overview.md)).

| Column | Purpose |
|---|---|
| `template_id` | Which visual style was used |
| `tex_source` | The compiled LaTeX source, kept for debugging/re-compilation and not re-served |
| `pdf_bytes` | The compiled PDF |

---

## Flow

All document-generation routes require the draft to be approved first (`resume_drafts.status == "approved"`). Content is locked from that point on, so it is safe to compile. Preview and finalize are rate-limited because each call can run a real `tectonic` compilation.

1. **List templates** (`GET /resumes/{draft_id}/templates`). Static catalog, no compilation.
2. **Preview** (`GET /resumes/{draft_id}/templates/{template_id}/preview`). Compiles on the fly and returns the PDF directly, without persisting anything, so the user can compare styles before committing. The frontend fetches the PDF bytes via axios and renders a same-origin `blob:` URL in an `<iframe>`, which keeps the inherited `X-Frame-Options: DENY` middleware untouched.
3. **Finalize** (`POST /resumes/{draft_id}/finalize`). Compiles and persists. This is the version `POST /applications` later snapshots.
4. **Fetch metadata** (`GET /resumes/{draft_id}/finalize`) and **Download** (`GET /resumes/{draft_id}/finalize/download`). Returns the persisted document's metadata or raw PDF bytes.

---

## Ownership and Access

No PBAC permission required. Scoped to the caller's own draft (see [Auth & Authorization](../auth/overview.md#no-pbac-on-manifestcvs-own-routes)).

---

## Testing

Most of `test_document_routes_integration.py` mocks `render_resume_pdf` because those tests verify the approval gate, ownership checks, and persistence around compilation, not compilation itself. Two tests deliberately use the real pipeline: `test_real_tectonic_finalize_produces_a_valid_pdf` and `test_real_tectonic_preview_compiles_without_persisting`. They exercise `markdown_to_latex` to `templates` to `tectonic_compiler` against realistic resume content containing LaTeX-special characters (`%`, `&`, `#`, `$`, `_`, `{`, `}`). These are the bugs a mocked `render_resume_pdf` cannot catch. The tests skip wherever `tectonic` is not on `PATH`. CI runs them inside the backend Docker image in the dedicated `real-tectonic` job.

---

## API Reference

See [API Reference](../api/reference.md) (Document Generation section) for the full request/response shapes.
