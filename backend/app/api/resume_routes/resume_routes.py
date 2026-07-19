from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...mystic_auth_adapter import get_current_user, get_user_id_by_email
from ...database.connection import database
from ..route_helpers import get_or_404

from ...resume_crud.resume_repository import resume_repository
from ...resume_table.resume_schema import ResumeDraftCreate, ResumeDraftUpdate, ResumeDraftRead

from ...ai_integration.gemini_client import generate_resume, refine_resume
from ...ai_integration.exceptions import AIIntegrationError
from ...auth.security.rate_limiter_service import rate_limiter_service
from ...retrieval.knowledge_retrieval_service import search_knowledge_base

# Self-service only, one user's own resume drafts — no PBAC permission
# required, same reasoning as career_knowledge_routes.py: ownership is
# enforced server-side by user_id-scoped queries, never a caller-supplied id.
router = APIRouter(prefix="/resumes", tags=["Resumes"])

# How many knowledge base excerpts to retrieve per generation/refinement —
# enough for a full resume's worth of sections without flooding the prompt.
_RETRIEVAL_TOP_K = 8


async def _current_user_id(current_user: dict, db: AsyncSession) -> int:
    user_id = await get_user_id_by_email(current_user["email"], db)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_id


async def _matching_chunks(user_id: int, query: str) -> list[str]:
    try:
        results = await search_knowledge_base(user_id, query, _RETRIEVAL_TOP_K)
    except AIIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if not results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your career knowledge base is empty — add your career information before generating a resume",
        )
    return [r["chunk"] for r in results]


@router.post("/", response_model=ResumeDraftRead, status_code=status.HTTP_201_CREATED)
# Retrieval + generation is a real-cost Gemini call per request — same
# rate-limiting protection as career_knowledge_routes.py's AI-triggering
# routes, keyed per-account. See docs/concerns/README.md's now-fixed "No
# rate limiting on AI-backed routes" entry.
@rate_limiter_service.rate_limited(
    "resume_create", account_key_func=lambda kwargs: kwargs["current_user"]["email"]
)
async def create_resume_draft(
    payload: ResumeDraftCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Starts a tailored resume for a job description (claude.md flow steps
    6-8): semantically retrieves the caller's own matching knowledge base
    excerpts, then AI generates an initial resume from them alone.
    """
    user_id = await _current_user_id(current_user, db)

    chunks = await _matching_chunks(user_id, payload.job_description)
    try:
        resume_content = await generate_resume(payload.job_description, chunks)
    except AIIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return await resume_repository.create(user_id, payload.job_description, resume_content, db)


@router.get("/", response_model=list[ResumeDraftRead])
async def list_my_resume_drafts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    return await resume_repository.list_by_user(user_id, db)


@router.get("/{draft_id}", response_model=ResumeDraftRead)
async def get_my_resume_draft(
    draft_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    return await get_or_404(
        resume_repository.get_by_id_and_user(draft_id, user_id, db), "Resume draft not found"
    )


@router.put("/{draft_id}", response_model=ResumeDraftRead)
# Rate-limited the same as create above — `content`-only edits are cheap,
# but PUT is the same endpoint the `refinement_prompt` AI-regeneration path
# uses, so the whole route is protected uniformly.
@rate_limiter_service.rate_limited(
    "resume_update", account_key_func=lambda kwargs: kwargs["current_user"]["email"]
)
async def update_my_resume_draft(
    draft_id: int,
    update_data: ResumeDraftUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Two edit paths (see ResumeDraftUpdate's docstring): `refinement_prompt`
    re-matches the knowledge base and regenerates via AI (steps 9-11);
    bare `content` is a direct manual edit (step 9), no AI call. Locked
    once approved (step 13) — see claude.md's Phase 3 rule that content
    can't change after approval.
    """
    user_id = await _current_user_id(current_user, db)
    draft = await get_or_404(
        resume_repository.get_by_id_and_user(draft_id, user_id, db), "Resume draft not found"
    )

    if draft.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This resume has been approved and its content is locked",
        )

    fields = update_data.model_dump(exclude_unset=True)
    if "refinement_prompt" in fields:
        refinement_prompt = fields.pop("refinement_prompt")
        query = f"{draft.job_description}\n\n{refinement_prompt}"
        chunks = await _matching_chunks(user_id, query)
        try:
            fields["resume_content"] = await refine_resume(
                draft.job_description, chunks, draft.resume_content or "", refinement_prompt
            )
        except AIIntegrationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    elif "content" in fields:
        fields["resume_content"] = fields.pop("content")

    return await resume_repository.update(draft, fields, db)


@router.post("/{draft_id}/approve", response_model=ResumeDraftRead)
async def approve_my_resume_draft(
    draft_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Locks a draft's content (claude.md flow step 13) — from here on, only
    template selection/finalization (Phase 3) may proceed; content edits
    are rejected by the PUT endpoint above.
    """
    user_id = await _current_user_id(current_user, db)
    draft = await get_or_404(
        resume_repository.get_by_id_and_user(draft_id, user_id, db), "Resume draft not found"
    )

    if not draft.resume_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve a resume with no content",
        )
    if draft.status == "approved":
        return draft

    return await resume_repository.update(draft, {"status": "approved"}, db)


@router.delete("/{draft_id}")
async def delete_my_resume_draft(
    draft_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    draft = await get_or_404(
        resume_repository.get_by_id_and_user(draft_id, user_id, db), "Resume draft not found"
    )
    await resume_repository.delete(draft, db)
    return {"detail": "Resume draft deleted"}
