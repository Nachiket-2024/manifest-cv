# SQLAlchemy's dynamically imported declarative base is runtime-correct but
# opaque to mypy; the repository's model boundaries validate these values.
# mypy: disable-error-code=arg-type

from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...ai_integration.exceptions import AIIntegrationError
from ...resume_builder import procrastinate_tasks  # noqa: F401
from ...resume_builder.ai_service import generate_structured_document
from ...resume_builder.artifact_model import ResumeRenderArtifact
from ...resume_builder.document_schema import validate_document
from ...resume_builder.job_model import ResumeJob
from ...resume_builder.models import ResumeRevision, ResumeWorkspace
from ...resume_builder.render_service import render_document_pdf
from ...retrieval.exceptions import RetrievalError
from ...retrieval.knowledge_retrieval_service import search_knowledge_base
from ...sdk import database, get_current_user
from ...storage.object_store import get_verified_bytes, put_bytes
from .resume_builder_routes import (
    JobRead,
    _owned,
    _user_id,
    router,
)

job_router = APIRouter(prefix="/resume-jobs", tags=["Resume Builder Jobs"])


async def _run_generation_job(job_id: int) -> None:
    async with database.async_session() as db:
        job = await db.get(ResumeJob, job_id)
        if job is None:
            return
        job.status = "running"
        await db.commit()
        try:
            workspace = await db.get(ResumeWorkspace, job.workspace_id)
            revision = await db.get(ResumeRevision, workspace.current_revision_id) if workspace else None
            if workspace is None or revision is None:
                raise ValueError("workspace revision not found")
            chunks = [item["chunk"] for item in await search_knowledge_base(workspace.user_id, workspace.job_description, 8)]
            if not chunks:
                raise ValueError("career knowledge is empty")
            document = await generate_structured_document(workspace.job_description, chunks, json.loads(revision.document_json))
            raw = json.dumps(document, sort_keys=True, separators=(",", ":"))
            next_revision = ResumeRevision(workspace_id=workspace.id, revision_number=revision.revision_number + 1, document_json=raw,
                                           content_hash=hashlib.sha256(raw.encode()).hexdigest(), change_kind="generated")
            db.add(next_revision)
            await db.flush()
            workspace.current_revision_id = next_revision.id
            job.result_revision_id = next_revision.id
            job.status = "succeeded"
            await db.commit()
        except (AIIntegrationError, RetrievalError, ValueError):
            job.status = "failed"
            job.error_code = "GENERATION_FAILED"
            job.error_message = "Resume generation failed"
            await db.commit()


async def _render_artifact(db: AsyncSession, workspace: ResumeWorkspace, revision: ResumeRevision) -> tuple[ResumeRenderArtifact, bytes]:
    existing = await db.execute(
        select(ResumeRenderArtifact)
        .where(ResumeRenderArtifact.revision_id == revision.id, ResumeRenderArtifact.status == "succeeded")
        .order_by(ResumeRenderArtifact.id.desc())
        .limit(1)
    )
    artifact = existing.scalar_one_or_none()
    if artifact is not None:
        return artifact, get_verified_bytes(artifact.storage_key, artifact.sha256)
    pdf = render_document_pdf(validate_document(json.loads(revision.document_json)))
    key = f"users/{workspace.user_id}/workspaces/{workspace.id}/revisions/{revision.id}/resume.pdf"
    byte_size, sha256 = put_bytes(key, pdf)
    artifact = ResumeRenderArtifact(
        revision_id=revision.id, storage_key=key, content_type="application/pdf",
        byte_size=byte_size, sha256=sha256,
    )
    db.add(artifact)
    await db.flush()
    return artifact, pdf


async def _run_render_job(job_id: int) -> None:
    async with database.async_session() as db:
        job = await db.get(ResumeJob, job_id)
        if job is None:
            return
        job.status = "running"
        await db.commit()
        try:
            workspace = await db.get(ResumeWorkspace, job.workspace_id)
            revision = await db.get(ResumeRevision, workspace.current_revision_id) if workspace else None
            if workspace is None or revision is None or workspace.status != "approved":
                raise ValueError("approved workspace revision not found")
            await _render_artifact(db, workspace, revision)
            job.result_revision_id = revision.id
            job.status = "succeeded"
            await db.commit()
        except (ValueError, OSError):
            job.status = "failed"
            job.error_code = "RENDER_FAILED"
            job.error_message = "Resume export failed; retry the export"
            await db.commit()


@job_router.get("/{job_id}", response_model=JobRead)
async def get_generation_job(job_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    user_id = await _user_id(current_user, db)
    result = await db.execute(select(ResumeJob).where(ResumeJob.id == job_id, ResumeJob.user_id == user_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Resume job not found")
    return job


@job_router.get("/{job_id}/download")
async def download_render_job(job_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    user_id = await _user_id(current_user, db)
    result = await db.execute(select(ResumeJob).where(ResumeJob.id == job_id, ResumeJob.user_id == user_id, ResumeJob.kind == "render"))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Resume export job not found")
    if job.status != "succeeded" or job.result_revision_id is None:
        raise HTTPException(status_code=409, detail="Resume export is not ready")
    artifact_result = await db.execute(
        select(ResumeRenderArtifact).where(
            ResumeRenderArtifact.revision_id == job.result_revision_id,
            ResumeRenderArtifact.status == "succeeded",
        ).order_by(ResumeRenderArtifact.id.desc()).limit(1)
    )
    artifact = artifact_result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Resume export artifact not found")
    return Response(
        content=get_verified_bytes(artifact.storage_key, artifact.sha256),
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="resume-{job.workspace_id}.pdf"', "X-Content-SHA256": artifact.sha256},
    )


@router.post("/{workspace_id}/generate-job", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def queue_generation_job(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    user_id = await _user_id(current_user, db)
    workspace = await _owned(workspace_id, user_id, db)
    if workspace.status == "approved":
        raise HTTPException(status_code=409, detail="Approved resumes are immutable")
    job = ResumeJob(user_id=user_id, workspace_id=workspace.id, kind="generate", status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await procrastinate_tasks.generate_resume_job.defer_async(job.id)
    return job


@router.post("/{workspace_id}/export-job", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def queue_export_job(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    user_id = await _user_id(current_user, db)
    workspace = await _owned(workspace_id, user_id, db)
    if workspace.status != "approved":
        raise HTTPException(status_code=409, detail="Approve the resume before exporting")
    job = ResumeJob(user_id=user_id, workspace_id=workspace.id, kind="render", status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await procrastinate_tasks.render_resume_job.defer_async(job.id)
    return job


@router.get("/{workspace_id}/export")
async def export_workspace(workspace_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(database.get_session)):
    workspace = await _owned(workspace_id, await _user_id(current_user, db), db)
    if workspace.status != "approved":
        raise HTTPException(status_code=409, detail="Approve the resume before exporting")
    revision = await db.get(ResumeRevision, workspace.current_revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Resume revision not found")
    artifact, pdf = await _render_artifact(db, workspace, revision)
    await db.commit()
    return Response(content=pdf, media_type=artifact.content_type, headers={"Content-Disposition": f'attachment; filename="resume-{workspace.id}.pdf"', "X-Content-SHA256": artifact.sha256})  # type: ignore[dict-item]
