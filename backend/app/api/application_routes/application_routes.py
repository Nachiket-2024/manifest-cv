from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...mystic_auth_adapter import get_current_user, get_user_id_by_email
from ...database.connection import database
from ..route_helpers import get_or_404

from ...resume_crud.resume_repository import resume_repository
from ...resume_document_crud.resume_document_repository import resume_document_repository
from ...application_crud.application_repository import application_repository
from ...application_table.application_schema import ApplicationCreate, ApplicationUpdate, ApplicationRead, ApplicationDetailRead

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
    Saves a tracked application (claude.md flow steps 19-23), snapshotting
    the finalized resume's content/template/PDF at this moment in time —
    see ApplicationRecord's docstring for why this copies rather than
    references its source.
    """
    user_id = await _current_user_id(current_user, db)

    draft = await get_or_404(
        resume_repository.get_by_id_and_user(payload.resume_draft_id, user_id, db), "Resume draft not found"
    )
    document = await resume_document_repository.get_by_draft_id(draft.id, db)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Finalize this resume (select a template) before saving an application",
        )

    fields = payload.model_dump(exclude={"resume_draft_id"})
    fields["resume_content_snapshot"] = draft.resume_content
    fields["template_id_snapshot"] = document.template_id
    fields["pdf_snapshot"] = document.pdf_bytes

    return await application_repository.create(user_id, fields, db)


@router.get("/", response_model=list[ApplicationRead])
async def list_my_applications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    return await application_repository.list_by_user(user_id, db)


@router.get("/{application_id}", response_model=ApplicationDetailRead)
async def get_my_application(
    application_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    return await get_or_404(
        application_repository.get_by_id_and_user(application_id, user_id, db), "Application not found"
    )


@router.get("/{application_id}/pdf")
async def download_my_application_pdf(
    application_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    application = await get_or_404(
        application_repository.get_by_id_and_user(application_id, user_id, db), "Application not found"
    )
    return Response(
        content=application.pdf_snapshot,
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
    application progresses — the resume snapshot itself is immutable, see
    ApplicationRecord's docstring.
    """
    user_id = await _current_user_id(current_user, db)
    application = await get_or_404(
        application_repository.get_by_id_and_user(application_id, user_id, db), "Application not found"
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
        application_repository.get_by_id_and_user(application_id, user_id, db), "Application not found"
    )
    await application_repository.delete(application, db)
    return {"detail": "Application deleted"}
