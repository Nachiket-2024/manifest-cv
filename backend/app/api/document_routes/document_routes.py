from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from mystic_auth.sdk import get_current_user, database, get_or_404, get_logger, rate_limiter_service
from ...manifestcv_sdk import get_user_id_by_email

from ...resume_crud.resume_repository import resume_repository
from ...resume_document_crud.resume_document_repository import resume_document_repository
from ...resume_document_table.resume_document_schema import (
    ResumeDocumentFinalize,
    ResumeDocumentRead,
    TemplateInfo,
)

from ...document_generation.templates import TEMPLATES, list_templates
from ...document_generation.resume_pdf_service import render_resume_pdf
from ...document_generation.exceptions import LatexCompilationError

# Nested under /resumes/{draft_id} — document generation always operates on
# one specific resume draft, never independently of it.
router = APIRouter(prefix="/resumes/{draft_id}", tags=["Resume Documents"])

logger = get_logger(__name__)


async def _current_user_id(current_user: dict, db: AsyncSession) -> int:
    user_id = await get_user_id_by_email(current_user["email"], db)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_id


async def _owned_approved_draft(draft_id: int, user_id: int, db: AsyncSession):
    """
    Fetches a draft owned by the caller and enforces claude.md's Phase 3
    rule that template preview/finalization only happens after the resume
    is approved (step 13) — content is locked from that point on, so it's
    safe to compile.
    """
    draft = await get_or_404(
        resume_repository.get_by_id_and_user(draft_id, user_id, db), "Resume draft not found"
    )
    if draft.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approve this resume before generating a document from it",
        )
    return draft


def _validate_template(template_id: str) -> None:
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown template: {template_id}")


@router.get("/templates", response_model=list[TemplateInfo])
async def list_resume_templates(
    draft_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """Available visual styles (claude.md's "template preview system") — static, no compilation."""
    user_id = await _current_user_id(current_user, db)
    await _owned_approved_draft(draft_id, user_id, db)
    return list_templates()


@router.get("/templates/{template_id}/preview")
# Each call shells out to tectonic for a real LaTeX compile (up to ~60s of
# CPU/wall time) — the same AI-route-grade rate limiting as career knowledge/
# resume generation applies here so a caller can't exhaust backend compute
# by hammering this endpoint. See docs/concerns/README.md.
@rate_limiter_service.rate_limited(
    "resume_document_preview", account_key_func=lambda kwargs: kwargs["current_user"]["email"]
)
async def preview_resume_template(
    draft_id: int,
    template_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Compiles the approved resume with one template on the fly and returns
    the PDF directly, without persisting anything — lets the user compare
    styles (step 15) before committing to one via POST .../finalize.
    """
    user_id = await _current_user_id(current_user, db)
    draft = await _owned_approved_draft(draft_id, user_id, db)
    _validate_template(template_id)

    try:
        _, pdf_bytes = await render_resume_pdf(draft.resume_content, template_id)
    except LatexCompilationError as exc:
        # Tectonic's raw stderr/stdout can include internal file paths/tool
        # diagnostics — logged in full for debugging, but never returned to
        # the caller verbatim (matches main.py's generic-500 policy for
        # unexpected failures elsewhere in the app).
        logger.warning("Template preview compilation failed for draft_id=%s: %s", draft_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to compile this resume — please try again"
        ) from exc

    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/finalize", response_model=ResumeDocumentRead)
# Same rate limiting as the preview route above — this is the persisting
# variant of the identical compile-on-demand operation.
@rate_limiter_service.rate_limited(
    "resume_document_finalize", account_key_func=lambda kwargs: kwargs["current_user"]["email"]
)
async def finalize_resume_document(
    draft_id: int,
    payload: ResumeDocumentFinalize,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Compiles and persists the final polished resume (steps 17-18). Storing
    it lets POST /applications later copy a snapshot without recompiling.
    """
    user_id = await _current_user_id(current_user, db)
    draft = await _owned_approved_draft(draft_id, user_id, db)
    _validate_template(payload.template_id)

    try:
        tex_source, pdf_bytes = await render_resume_pdf(draft.resume_content, payload.template_id)
    except LatexCompilationError as exc:
        logger.warning("Resume finalize compilation failed for draft_id=%s: %s", draft_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to compile this resume — please try again"
        ) from exc

    return await resume_document_repository.upsert(draft_id, payload.template_id, tex_source, pdf_bytes, db)


@router.get("/finalize", response_model=ResumeDocumentRead)
async def get_finalized_resume_document(
    draft_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    await _owned_approved_draft(draft_id, user_id, db)
    document = await resume_document_repository.get_by_draft_id(draft_id, db)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This resume hasn't been finalized yet")
    return document


@router.get("/finalize/download")
async def download_finalized_resume_document(
    draft_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    await _owned_approved_draft(draft_id, user_id, db)
    document = await resume_document_repository.get_by_draft_id(draft_id, db)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This resume hasn't been finalized yet")

    return Response(
        content=document.pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="resume-{draft_id}.pdf"'},
    )
