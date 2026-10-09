# SQLAlchemy's dynamically imported declarative base is runtime-correct but
# opaque to mypy; the repository's model boundaries validate these values.
# mypy: disable-error-code=arg-type

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...app_sdk import get_user_id_by_email
from ...application_crud.application_repository import application_repository
from ...application_table.application_schema import (
    ApplicationCreate,
    ApplicationDetailRead,
    ApplicationRead,
    ApplicationUpdate,
)
from ...resume_builder.artifact_model import ResumeRenderArtifact
from ...resume_builder.document_schema import validate_document
from ...resume_builder.models import ResumeRevision, ResumeWorkspace
from ...resume_builder.render_service import render_document_pdf
from ...sdk import database, get_current_user, get_or_404
from ...storage.object_store import get_verified_bytes, put_bytes

router = APIRouter(prefix="/applications", tags=["Applications"])


async def _current_user_id(current_user: dict, db: AsyncSession) -> int:
    user_id = await get_user_id_by_email(current_user["email"], db)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_id


@router.post("/", response_model=ApplicationDetailRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Saves a tracked application, snapshotting the finalized resume's
    content/template/PDF at this moment in time. See ApplicationRecord's
    docstring for why this copies rather than references its source.
    """
    user_id = await _current_user_id(current_user, db)

    fields = payload.model_dump(exclude={"workspace_id"})
    workspace_result = await db.execute(select(ResumeWorkspace).where(ResumeWorkspace.id == payload.workspace_id, ResumeWorkspace.user_id == user_id))
    workspace = workspace_result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Resume workspace not found")
    if workspace.status != "approved":
        raise HTTPException(status_code=400, detail="Approve the resume before creating an application")
    revision = await db.get(ResumeRevision, workspace.current_revision_id)
    if revision is None:
        raise HTTPException(status_code=400, detail="Resume revision not found")
    document_json = revision.document_json
    document = validate_document(json.loads(document_json))
    artifact_result = await db.execute(
        select(ResumeRenderArtifact)
        .where(ResumeRenderArtifact.revision_id == revision.id, ResumeRenderArtifact.status == "succeeded")
        .order_by(ResumeRenderArtifact.id.desc())
        .limit(1)
    )
    artifact = artifact_result.scalar_one_or_none()
    if artifact is None:
        pdf = render_document_pdf(document)
        key = f"users/{user_id}/workspaces/{workspace.id}/revisions/{revision.id}/resume.pdf"
        byte_size, sha256 = put_bytes(key, pdf)
        artifact = ResumeRenderArtifact(
            revision_id=revision.id, storage_key=key, content_type="application/pdf",
            byte_size=byte_size, sha256=sha256,
        )
        db.add(artifact)
        await db.flush()
    else:
        pdf = get_verified_bytes(artifact.storage_key, artifact.sha256)
    fields.update({"resume_content_snapshot": document_json, "template_id_snapshot": workspace.template_key, "template_version_snapshot": "1",
                   "pdf_snapshot": pdf, "pdf_storage_key_snapshot": artifact.storage_key,
                   "pdf_sha256_snapshot": artifact.sha256,
                   "resume_workspace_id": workspace.id, "resume_revision_id": revision.id,
                   "document_snapshot": document_json})

    return await application_repository.create(user_id, fields, db)


@router.get("/", response_model=list[ApplicationRead])
async def list_my_applications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """Newest first, paginated. See docs/app/applications/overview.md#pagination."""
    user_id = await _current_user_id(current_user, db)
    return await application_repository.list_by_user(user_id, db, limit=limit, offset=offset)


@router.get("/{application_id}", response_model=ApplicationDetailRead)
async def get_my_application(
    application_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    return await get_or_404(
        application_repository.get_by_id_and_user(application_id, user_id, db), "Application not found", code="APPLICATION_NOT_FOUND"
    )


@router.get("/{application_id}/pdf")
async def download_my_application_pdf(
    application_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    application = await get_or_404(
        application_repository.get_by_id_and_user(application_id, user_id, db), "Application not found", code="APPLICATION_NOT_FOUND"
    )
    pdf = get_verified_bytes(application.pdf_storage_key_snapshot, application.pdf_sha256_snapshot) if application.pdf_storage_key_snapshot and application.pdf_sha256_snapshot else application.pdf_snapshot
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="application-{application_id}.pdf"'},
    )


@router.patch("/{application_id}", response_model=ApplicationDetailRead)
async def update_my_application(
    application_id: int,
    update_data: ApplicationUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Updates tracking fields only (company/date/time/status) as an
    application progresses. The resume snapshot itself is immutable, see
    ApplicationRecord's docstring.
    """
    user_id = await _current_user_id(current_user, db)
    application = await get_or_404(
        application_repository.get_by_id_and_user(application_id, user_id, db), "Application not found", code="APPLICATION_NOT_FOUND"
    )
    fields = update_data.model_dump(exclude_unset=True)
    return await application_repository.update(application, fields, db)


@router.delete("/{application_id}")
async def delete_my_application(
    application_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    application = await get_or_404(
        application_repository.get_by_id_and_user(application_id, user_id, db), "Application not found", code="APPLICATION_NOT_FOUND"
    )
    await application_repository.delete(application, db)
    return {"detail": "Application deleted"}
