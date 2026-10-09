from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from backend.app.api.resume_builder_routes import job_routes
from backend.app.api.resume_builder_routes import resume_builder_routes as routes
from backend.app.resume_builder import (
    ai_service,
    html_renderer,
    render_service,
    security,
)
from backend.app.resume_builder.templates import template_document
from backend.app.storage import object_store


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class _DB:
    def __init__(self, *results):
        self.results = list(results)
        self.added = []

    async def execute(self, _statement):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.added[-1].id = 44

    async def commit(self):
        return None

    async def refresh(self, _value):
        return None

    async def get(self, _model, _value):
        return self.results.pop(0).value

    async def delete(self, _value):
        return None


class _SessionContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *_args):
        return None


def test_markdown_to_blocks_maps_headings_and_list_content() -> None:
    existing = [
        {"id": "summary", "type": "summary", "title": "Summary", "content": {}},
        {"id": "skills", "type": "skills", "title": "Skills", "content": {}},
    ]
    blocks = ai_service.markdown_to_blocks(
        "# Summary\nA concise profile\n## Skills\n- Python\n- SQL", existing
    )
    assert blocks[0]["content"]["text"] == "A concise profile"
    assert blocks[1]["content"]["bullets"] == ["Python", "SQL"]


@pytest.mark.asyncio
async def test_generate_structured_document_preserves_document_and_replaces_blocks(monkeypatch) -> None:
    async def fake_generate(_job_description: str, _chunks: list[str]) -> str:
        return "# Summary\nGenerated summary"

    monkeypatch.setattr(ai_service, "generate_resume", fake_generate)
    original = {"pages": [], "blocks": [{"id": "summary", "type": "summary", "title": "Summary"}]}
    generated = await ai_service.generate_structured_document("role", ["evidence"], original)
    assert generated["pages"] == []
    assert generated["blocks"][0]["content"]["text"] == "Generated summary"


def test_security_accepts_safe_values_and_rejects_limits() -> None:
    for value in ("https://example.com", "mailto:person@example.com", {"items": ["ok", 3]}):
        security.validate_content(value)
    with pytest.raises(ValueError, match="unsupported executable"):
        security.validate_content("<img onload=alert(1)>")
    with pytest.raises(ValueError, match="too many fields"):
        security.validate_content({str(index): index for index in range(201)})
    with pytest.raises(ValueError, match="too many items"):
        security.validate_content(list(range(201)))


def test_html_renderer_handles_hidden_blocks_lists_and_line_breaks() -> None:
    document = template_document("classic_single_column")
    document.blocks[0].content = {"name": "A & B", "headline": "Line 1\nLine 2", "items": ["one", 2, ""]}
    document.blocks[1].visible = False
    rendered = html_renderer.render_document_html(document)
    assert "A &amp; B" in rendered
    assert "Line 1<br>Line 2" in rendered
    assert "<li>one</li>" in rendered and "<li>2</li>" in rendered


def test_pdf_renderer_uses_letter_media_box_and_escapes_text() -> None:
    document = template_document("classic_single_column")
    document.paper = "letter"
    document.blocks[0].content = {"text": "parentheses (safe)"}
    pdf = render_service.render_document_pdf(document)
    assert b"[0 0 612 792]" in pdf
    assert b"parentheses \\(safe\\)" in pdf


def test_object_store_local_round_trip_and_fail_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(object_store, "_ROOT", tmp_path.resolve())
    monkeypatch.setattr(object_store, "_S3_ENDPOINT", "")
    monkeypatch.setattr(object_store, "_S3_CLIENT", None)
    size, digest = object_store.put_bytes("nested/resume.pdf", b"pdf")
    assert size == 3
    assert object_store.get_verified_bytes("nested/resume.pdf", digest) == b"pdf"
    with pytest.raises(ValueError, match="checksum"):
        object_store.get_verified_bytes("nested/resume.pdf", "0" * 64)
    with pytest.raises(ValueError, match="invalid storage key"):
        object_store.put_bytes("../outside.pdf", b"pdf")
    with pytest.raises(ValueError, match="exceeds size"):
        object_store.put_bytes("large.pdf", b"pdf", max_bytes=2)


def test_object_store_s3_adapter_creates_bucket_and_round_trips(monkeypatch) -> None:
    class Client:
        def __init__(self):
            self.objects = {}

        def head_bucket(self, **_kwargs):
            raise RuntimeError("bucket missing")

        def create_bucket(self, **_kwargs):
            return None

        def put_object(self, *, Key, Body, **_kwargs):
            self.objects[Key] = Body

        def get_object(self, *, Key, **_kwargs):
            return {"Body": SimpleNamespace(read=lambda: self.objects[Key])}

    client = Client()
    monkeypatch.setattr(object_store, "_S3_ENDPOINT", "http://seaweedfs:8333")
    monkeypatch.setattr(object_store, "_S3_CLIENT", None)
    monkeypatch.setattr(object_store, "_S3_BUCKET_READY", False)
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *_args, **_kwargs: client))
    size, digest = object_store.put_bytes("s3/resume.pdf", b"pdf")
    assert size == 3 and object_store.get_verified_bytes("s3/resume.pdf", digest) == b"pdf"


@pytest.mark.asyncio
async def test_render_artifact_creates_and_reuses_private_storage(monkeypatch) -> None:
    document = template_document("classic_single_column")
    revision = SimpleNamespace(id=7, document_json=json.dumps(document.model_dump(mode="json")))
    workspace = SimpleNamespace(id=3, user_id=9)
    db = _DB(_Result(None))
    monkeypatch.setattr(job_routes, "render_document_pdf", lambda _document: b"pdf")
    monkeypatch.setattr(job_routes, "put_bytes", lambda _key, data: (len(data), "a" * 64))
    artifact, content = await job_routes._render_artifact(db, workspace, revision)
    assert content == b"pdf"
    assert artifact.storage_key.endswith("/revisions/7/resume.pdf")
    assert artifact.sha256 == "a" * 64

    existing = SimpleNamespace(storage_key="cached.pdf", sha256="b" * 64)
    db = _DB(_Result(existing))
    monkeypatch.setattr(job_routes, "get_verified_bytes", lambda _key, _sha: b"cached")
    cached, content = await job_routes._render_artifact(db, workspace, revision)
    assert cached is existing and content == b"cached"


@pytest.mark.asyncio
async def test_export_job_queue_and_download_are_user_scoped(monkeypatch) -> None:
    workspace = SimpleNamespace(id=3, user_id=9, status="approved")
    db = _DB()
    monkeypatch.setattr(job_routes, "_user_id", lambda _user, _db: _return(9))
    monkeypatch.setattr(job_routes, "_owned", lambda _workspace_id, _user_id, _db: _return(workspace))
    async def defer(_job_id: int) -> None:
        return None

    monkeypatch.setattr(job_routes.procrastinate_tasks.render_resume_job, "defer_async", defer)
    job = await job_routes.queue_export_job(3, {}, db)
    assert job.kind == "render" and job.status == "queued"

    stored_job = SimpleNamespace(id=12, workspace_id=3, user_id=9, kind="render", status="succeeded", result_revision_id=7)
    artifact = SimpleNamespace(content_type="application/pdf", storage_key="resume.pdf", sha256="c" * 64)
    download_db = _DB(_Result(stored_job), _Result(artifact))
    monkeypatch.setattr(job_routes, "get_verified_bytes", lambda _key, _sha: b"%PDF-1.4")
    response = await job_routes.download_render_job(12, {"email": "user@example.com"}, download_db)
    assert response.body == b"%PDF-1.4"
    assert response.headers["x-content-sha256"] == "c" * 64


@pytest.mark.asyncio
async def test_route_guards_and_preview_export_paths(monkeypatch) -> None:
    with pytest.raises(Exception, match="Template not found"):
        await routes.template("missing")

    workspace = SimpleNamespace(id=3, user_id=9, status="draft", current_revision_id=7)
    document = template_document("classic_single_column")
    revision = SimpleNamespace(
        id=7,
        workspace_id=3,
        document_json=json.dumps(document.model_dump(mode="json")),
    )
    monkeypatch.setattr(job_routes, "_user_id", lambda _user, _db: _return(9))
    monkeypatch.setattr(job_routes, "_owned", lambda _workspace_id, _user_id, _db: _return(workspace))
    monkeypatch.setattr(routes, "_user_id", lambda _user, _db: _return(9))
    monkeypatch.setattr(routes, "_owned", lambda _workspace_id, _user_id, _db: _return(workspace))
    with pytest.raises(Exception, match="Approve the resume"):
        await job_routes.export_workspace(3, {}, _DB())

    workspace.status = "approved"
    export_db = _DB()
    export_db.results.append(_Result(revision))
    monkeypatch.setattr(
        job_routes,
        "_render_artifact",
        lambda _db, _workspace, _revision: _return(
            (SimpleNamespace(content_type="application/pdf", sha256="d" * 64), b"pdf")
        ),
    )
    exported = await job_routes.export_workspace(3, {}, export_db)
    assert exported.body == b"pdf"
    preview_db = _DB()
    preview_db.results.append(_Result(revision))
    preview = await routes.preview_workspace(3, {}, preview_db)
    assert preview.media_type == "text/html; charset=utf-8" and b"<!doctype html>" in preview.body


@pytest.mark.asyncio
async def test_route_identity_and_job_not_found_guards(monkeypatch) -> None:
    monkeypatch.setattr(routes, "get_user_id_by_email", lambda _email, _db: _return(None))
    with pytest.raises(Exception, match="User not found"):
        await routes._user_id({"email": "missing@example.com"}, _DB())
    with pytest.raises(Exception, match="Resume workspace not found"):
        await routes._owned(3, 9, _DB(_Result(None)))
    monkeypatch.setattr(job_routes, "_user_id", lambda _user, _db: _return(9))
    with pytest.raises(Exception, match="Resume job not found"):
        await job_routes.get_generation_job(12, {}, _DB(_Result(None)))


@pytest.mark.asyncio
async def test_create_workspace_persists_initial_template_revision(monkeypatch) -> None:
    monkeypatch.setattr(routes, "_user_id", lambda _user, _db: _return(9))
    db = _DB()
    workspace = await routes.create_workspace(
        routes.WorkspaceCreate(title="New", job_description="Role"), {}, db
    )
    assert workspace.current_revision_id == 44
    assert len(db.added) == 2


@pytest.mark.asyncio
async def test_background_render_and_generation_jobs_update_persisted_state(monkeypatch) -> None:
    render_job = SimpleNamespace(id=12, workspace_id=3, status="queued")
    workspace = SimpleNamespace(id=3, user_id=9, status="approved", current_revision_id=7, job_description="Role")
    revision = SimpleNamespace(
        id=7,
        revision_number=1,
        document_json=json.dumps(template_document("classic_single_column").model_dump(mode="json")),
    )
    render_db = _DB()
    render_db.get = lambda model, _id: _return(
        render_job if model is job_routes.ResumeJob else workspace if model is job_routes.ResumeWorkspace else revision
    )
    monkeypatch.setattr(job_routes.database, "async_session", lambda: _SessionContext(render_db))
    monkeypatch.setattr(job_routes, "_render_artifact", lambda *_args: _return((None, b"pdf")))
    await job_routes._run_render_job(12)
    assert render_job.status == "succeeded" and render_job.result_revision_id == 7

    generation_job = SimpleNamespace(id=13, workspace_id=3, status="queued")
    generation_db = _DB()
    generation_db.get = lambda model, _id: _return(
        generation_job if model is job_routes.ResumeJob else workspace if model is job_routes.ResumeWorkspace else revision
    )
    monkeypatch.setattr(job_routes.database, "async_session", lambda: _SessionContext(generation_db))
    monkeypatch.setattr(job_routes, "search_knowledge_base", lambda *_args: _return([{"chunk": "evidence"}]))
    monkeypatch.setattr(job_routes, "generate_structured_document", lambda *_args: _return(json.loads(revision.document_json)))
    await job_routes._run_generation_job(13)
    assert generation_job.status == "succeeded" and generation_job.result_revision_id == 44

    failed_render_job = SimpleNamespace(id=14, workspace_id=3, status="queued")
    failed_workspace = SimpleNamespace(
        id=workspace.id,
        user_id=workspace.user_id,
        status="draft",
        current_revision_id=workspace.current_revision_id,
        job_description=workspace.job_description,
    )
    failed_db = _DB()
    failed_db.get = lambda model, _id: _return(
        failed_render_job if model is job_routes.ResumeJob else failed_workspace if model is job_routes.ResumeWorkspace else revision
    )
    monkeypatch.setattr(job_routes.database, "async_session", lambda: _SessionContext(failed_db))
    await job_routes._run_render_job(14)
    assert failed_render_job.status == "failed"

    empty_job = SimpleNamespace(id=15, workspace_id=3, status="queued")
    empty_db = _DB()
    empty_db.get = lambda model, _id: _return(
        empty_job if model is job_routes.ResumeJob else workspace if model is job_routes.ResumeWorkspace else revision
    )
    monkeypatch.setattr(job_routes.database, "async_session", lambda: _SessionContext(empty_db))
    monkeypatch.setattr(job_routes, "search_knowledge_base", lambda *_args: _return([]))
    await job_routes._run_generation_job(15)
    assert empty_job.status == "failed"


async def _return(value):
    return value
