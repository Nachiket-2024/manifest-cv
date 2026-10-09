# SQLAlchemy's dynamically imported declarative base is runtime-correct but
# opaque to mypy; the repository's model boundaries validate these values.
# mypy: disable-error-code=arg-type

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...ai_integration.exceptions import AIIntegrationError
from ...ai_integration.gemini_client import refine_resume
from ...app_sdk import get_user_id_by_email
from ...resume_builder.ai_service import generate_structured_document, markdown_to_blocks
from ...resume_builder.document_schema import validate_document
from ...resume_builder.html_renderer import render_document_html
from ...resume_builder.models import ResumeRevision, ResumeWorkspace
from ...resume_builder.templates import get_template, list_templates, template_document
from ...retrieval.exceptions import RetrievalError
from ...retrieval.knowledge_retrieval_service import search_knowledge_base
from ...sdk import database, get_current_user

router = APIRouter(prefix="/resume-workspaces", tags=["Resume Builder"])
class WorkspaceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    job_description: str = Field(min_length=1, max_length=50_000)
    template_key: str = "classic_single_column"


class DocumentSave(BaseModel):
    document: dict
    expected_revision_id: int | None = None
    change_kind: str = Field(default="manual_edit", pattern="^(manual_edit|template_change|layout_change|restored|generated|ai_refinement)$")


class RefineRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2_000)


class DocumentProposalRead(BaseModel):
    document: dict
    source_revision_id: int


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    job_description: str
    template_key: str
    status: str
    current_revision_id: int | None
    created_at: datetime
    updated_at: datetime

class RevisionRead(BaseModel):
    id: int
    workspace_id: int
    revision_number: int
    document: dict
    content_hash: str
    change_kind: str
    created_at: datetime


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    kind: str
    status: str
    result_revision_id: int | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

async def _user_id(current_user: dict, db: AsyncSession) -> int:
    value = await get_user_id_by_email(current_user["email"], db)
    if value is None:
        raise HTTPException(status_code=404, detail="User not found")
    return value


async def _owned(workspace_id: int, user_id: int, db: AsyncSession) -> ResumeWorkspace:
    result = await db.execute(select(ResumeWorkspace).where(ResumeWorkspace.id == workspace_id, ResumeWorkspace.user_id == user_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Resume workspace not found")
    return workspace


def _read_revision(revision: ResumeRevision) -> RevisionRead:
    return RevisionRead(id=revision.id, workspace_id=revision.workspace_id, revision_number=revision.revision_number,
                        document=json.loads(revision.document_json), content_hash=revision.content_hash,
                        change_kind=revision.change_kind, created_at=revision.created_at)


@router.get("/templates")
async def templates() -> list[dict]:
    return list_templates()


@router.get("/templates/{template_key}")
async def template(template_key: str) -> dict:
    value = get_template(template_key)
    if value is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return value


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    try:
        document = template_document(payload.template_key)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail="Unsupported template") from exc
    raw = json.dumps(document.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    workspace = ResumeWorkspace(user_id=await _user_id(current_user, db), title=payload.title, job_description=payload.job_description, template_key=payload.template_key)
    db.add(workspace)
    await db.flush()
    revision = ResumeRevision(workspace_id=workspace.id, revision_number=1, document_json=raw,
                              content_hash=hashlib.sha256(raw.encode()).hexdigest(), change_kind="generated")
    db.add(revision)
    await db.flush()
    workspace.current_revision_id = revision.id
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    result = await db.execute(select(ResumeWorkspace).where(ResumeWorkspace.user_id == await _user_id(current_user, db)).order_by(ResumeWorkspace.updated_at.desc()).limit(limit).offset(offset))
    return list(result.scalars().all())


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    revision = await db.get(ResumeRevision, workspace.current_revision_id) if workspace.current_revision_id else None
    return {"workspace": WorkspaceRead.model_validate(workspace), "revision": _read_revision(revision) if revision else None}


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    await db.delete(workspace)
    await db.commit()


@router.put("/{workspace_id}/document")
async def save_document(workspace_id: int, payload: DocumentSave, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    if workspace.status == "approved":
        raise HTTPException(status_code=409, detail="Approved resumes are immutable")
    if payload.expected_revision_id is not None and payload.expected_revision_id != workspace.current_revision_id:
        raise HTTPException(status_code=409, detail="Resume changed elsewhere; reload before saving")
    try:
        document = validate_document(payload.document)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid resume layout or content") from exc
    result = await db.execute(select(ResumeRevision).where(ResumeRevision.workspace_id == workspace.id).order_by(ResumeRevision.revision_number.desc()).limit(1))
    previous = result.scalar_one_or_none()
    number = (previous.revision_number if previous else 0) + 1
    raw = json.dumps(document.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    revision = ResumeRevision(workspace_id=workspace.id, revision_number=number, document_json=raw,
                              content_hash=hashlib.sha256(raw.encode()).hexdigest(), change_kind=payload.change_kind)
    db.add(revision)
    await db.flush()
    workspace.current_revision_id = revision.id
    await db.commit()
    await db.refresh(revision)
    return _read_revision(revision)


@router.post("/{workspace_id}/generate", response_model=RevisionRead)
async def generate_workspace_document(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    if workspace.status == "approved":
        raise HTTPException(status_code=409, detail="Approved resumes are immutable")
    revision = await db.get(ResumeRevision, workspace.current_revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Resume revision not found")
    try:
        chunks = [item["chunk"] for item in await search_knowledge_base(workspace.user_id, workspace.job_description, 8)]
        if not chunks:
            raise HTTPException(status_code=400, detail="Add career knowledge before generating a resume")
        document = await generate_structured_document(workspace.job_description, chunks, json.loads(revision.document_json))
    except (AIIntegrationError, RetrievalError) as exc:
        raise HTTPException(status_code=502, detail="Resume generation failed") from exc
    return await save_document(workspace_id, DocumentSave(document=document, expected_revision_id=workspace.current_revision_id, change_kind="generated"), current_user, db)


@router.post("/{workspace_id}/refine", response_model=RevisionRead)
async def refine_workspace_document(workspace_id: int, payload: RefineRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    if workspace.status == "approved":
        raise HTTPException(status_code=409, detail="Approved resumes are immutable")
    revision = await db.get(ResumeRevision, workspace.current_revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Resume revision not found")
    try:
        chunks = [item["chunk"] for item in await search_knowledge_base(workspace.user_id, f"{workspace.job_description}\n{payload.prompt}", 8)]
        generated = await refine_resume(workspace.job_description, chunks, revision.document_json, payload.prompt)
        current = json.loads(revision.document_json)
        document = {**current, "blocks": markdown_to_blocks(generated, current["blocks"])}
    except (AIIntegrationError, RetrievalError) as exc:
        raise HTTPException(status_code=502, detail="Resume refinement failed") from exc
    return await save_document(workspace_id, DocumentSave(document=document, expected_revision_id=workspace.current_revision_id, change_kind="ai_refinement"), current_user, db)


@router.post("/{workspace_id}/refine/preview", response_model=DocumentProposalRead)
async def preview_refinement(workspace_id: int, payload: RefineRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    """Generate an explicit proposal without changing the current revision."""
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    if workspace.status == "approved":
        raise HTTPException(status_code=409, detail="Approved resumes are immutable")
    revision = await db.get(ResumeRevision, workspace.current_revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Resume revision not found")
    try:
        chunks = [item["chunk"] for item in await search_knowledge_base(workspace.user_id, f"{workspace.job_description}\n{payload.prompt}", 8)]
        generated = await refine_resume(workspace.job_description, chunks, revision.document_json, payload.prompt)
        current = json.loads(revision.document_json)
        document = validate_document({**current, "blocks": markdown_to_blocks(generated, current["blocks"])})
    except (AIIntegrationError, RetrievalError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Resume refinement preview failed") from exc
    return DocumentProposalRead(document=document.model_dump(mode="json"), source_revision_id=revision.id)


@router.get("/{workspace_id}/revisions", response_model=list[RevisionRead])
async def revisions(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    result = await db.execute(select(ResumeRevision).where(ResumeRevision.workspace_id == workspace.id).order_by(ResumeRevision.revision_number.desc()))
    return [_read_revision(item) for item in result.scalars().all()]


@router.post("/{workspace_id}/revisions/{revision_id}/restore", response_model=RevisionRead)
async def restore_revision(workspace_id: int, revision_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    if workspace.status == "approved":
        raise HTTPException(status_code=409, detail="Approved resumes are immutable")
    source = await db.get(ResumeRevision, revision_id)
    if source is None or source.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Revision not found")
    payload = DocumentSave(document=json.loads(source.document_json), expected_revision_id=workspace.current_revision_id, change_kind="restored")
    return await save_document(workspace_id, payload, current_user, db)


@router.post("/{workspace_id}/approve", response_model=WorkspaceRead)
async def approve_workspace(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    workspace.status = "approved"  # type: ignore[assignment]
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("/{workspace_id}/preview", response_class=Response)
async def preview_workspace(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    revision = await db.get(ResumeRevision, workspace.current_revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Resume revision not found")
    document = validate_document(json.loads(revision.document_json))
    return Response(content=render_document_html(document), media_type="text/html; charset=utf-8", headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"})
