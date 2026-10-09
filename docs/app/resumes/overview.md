# Resume Studio

---

Resume Studio is ManifestCV's workspace for building tailored resumes. Each workspace keeps the job description, selected template, current structured document, and revision history together.

## Product flow

---

```mermaid
%%{init: {"themeVariables": {"lineColor": "#334155"}} }%%
flowchart TD
    Start["Create workspace"] --> Setup["Title + job description"]
    Setup --> Template["Choose template"]
    Template --> Edit["Edit structured document"]
    Edit --> Revision["Save revision"]
    Revision --> Refine["Generate or refine with AI"]
    Refine --> Revision
    Revision --> Approve{"Approve current revision?"}
    Approve -->|"No"| Edit
    Approve -->|"Yes"| Export["Preview and export PDF"]
    Export --> Snapshot["Optional application snapshot"]
    classDef success fill:#dcfce7,stroke:#16a34a
    classDef blocked fill:#fee2e2,stroke:#dc2626
    classDef decision fill:#eff6ff,stroke:#3b82f6
    class Export,Snapshot success
    class Approve decision
```

---

1. Open Resume Studio and create a workspace.
2. Add a resume title and the target job description.
3. Review the available layouts and choose a template.
4. Edit the document on the canvas with the block library and inspector.
5. Generate or refine content with the career knowledge base when needed.
6. Review revisions, approve the document, and export the finished resume.

## Frontend

---

The active flow lives in `frontend/src/app/resume_builder/`:

- `ResumeWorkspacesPage.tsx` lists workspaces and starts a new one.
- `ResumeSetupPage.tsx` collects the title and job description.
- `ResumeTemplatePickerPage.tsx` previews and selects layouts.
- `ResumeBuilderPage.tsx` provides the document canvas, inspector, block library, AI refinement, revision history, and export controls.

The routes are `/resume-builder`, `/resume-builder/new`, `/resume-builder/new/templates`, and `/resume-builder/:workspaceId`.

## Backend

---

The workspace API lives under `/resume-workspaces`. It provides template catalog, workspace creation, document saves, generation, refinement, revision history, restore, approval, background jobs, and export. Workspace ownership is enforced for every user resource.

### Background jobs

Generation and PDF export are queued on the shared Procrastinate worker. The API returns a job id, and the frontend polls `/resume-jobs/{job_id}` until the job succeeds or fails. A successful generation creates a new revision; a successful export stores a PDF artifact. See [API Reference](../api/reference.md#resume-studio) for the job and download routes.

```mermaid
%%{init: {"themeVariables": {"lineColor": "#334155"}} }%%
sequenceDiagram
    participant UI as Resume Studio
    participant API as ManifestCV API
    participant DB as PostgreSQL queue and job state
    participant Worker as Procrastinate worker
    participant Provider as Gemini or Tectonic
    UI->>API: Queue generation or export
    API->>DB: Save job and enqueue task
    API-->>UI: Return job id (202)
    Worker->>DB: Claim queued job
    Worker->>Provider: Generate content or render PDF
    Provider-->>Worker: Result or failure
    Worker->>DB: Save revision or artifact and status
    UI->>API: Poll job status
    API-->>UI: queued, running, succeeded, or failed
```

The structured document schema is defined in `backend/app/resume_builder/document_schema.py`. Templates are defined in `backend/app/resume_builder/templates.py`. Revision rows preserve each saved document and its change kind so the editor can restore earlier work safely.

## Related areas

---

Career Knowledge supplies the private source material used for generation and refinement. Applications store a snapshot of the selected resume at the time an application is tracked. Document export is part of the Resume Studio workspace flow.
