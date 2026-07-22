from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...sdk import get_current_user, capture_exception, database, get_or_404, get_logger, rate_limiter_service
from ...manifestcv_sdk import get_user_id_by_email

from ...career_knowledge_crud.career_knowledge_repository import career_knowledge_repository
from ...career_knowledge_table.career_knowledge_schema import (
    CareerKnowledgeBaseCreate,
    CareerKnowledgeBaseUpdate,
    CareerKnowledgeBaseRead,
    CareerKnowledgeSearchResult,
)

from ...ai_integration.gemini_client import structure_knowledge_base
from ...ai_integration.exceptions import AIIntegrationError
from ...retrieval.exceptions import RetrievalError
from ...retrieval.knowledge_retrieval_service import (
    index_knowledge_base,
    delete_knowledge_base,
    search_knowledge_base,
)

# Self-service only, one knowledge base per authenticated user — no PBAC
# permission is required (same reasoning as audit_log_routes.py's
# /security-log/me: reading/editing one's own private data isn't a
# privileged operation, and ownership is enforced server-side by
# user_id-scoped queries, never by a caller-supplied id).
router = APIRouter(prefix="/career-knowledge", tags=["Career Knowledge"])

logger = get_logger(__name__)


async def _current_user_id(current_user: dict, db: AsyncSession) -> int:
    user_id = await get_user_id_by_email(current_user["email"], db)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_id


async def _structure_or_502(raw_input: str) -> str:
    try:
        return await structure_knowledge_base(raw_input)
    except AIIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


async def _reindex_best_effort(user_id: int, content: str) -> None:
    """
    The Postgres write this always runs after is the source of truth and
    has already committed by the time this is called — a Qdrant failure
    here doesn't mean the caller's save failed, just that search over this
    knowledge base is stale until the next successful save. Reported to
    error monitoring so it's visible to an operator, but deliberately never
    raised: turning this into a 502 would tell the caller their save failed
    when it didn't, and (for the create route specifically) leave them
    unable to usefully retry — a second POST would just 409, since the row
    already exists.
    """
    try:
        await index_knowledge_base(user_id, content)
    except (AIIntegrationError, RetrievalError) as exc:
        logger.warning("Career knowledge base saved but re-indexing failed for user_id=%s: %s", user_id, exc)
        await capture_exception(exc)


async def _delete_index_best_effort(user_id: int) -> None:
    """Same reasoning as _reindex_best_effort — the DB row is already gone."""
    try:
        await delete_knowledge_base(user_id)
    except (AIIntegrationError, RetrievalError) as exc:
        logger.warning("Career knowledge base deleted but Qdrant cleanup failed for user_id=%s: %s", user_id, exc)
        await capture_exception(exc)


@router.post("/", response_model=CareerKnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
# Every call here triggers a Gemini structuring call plus a Qdrant index —
# both real cost/latency, unlike a plain CRUD write — so this gets the same
# rate-limiting protection as auth's expensive endpoints (signup/login),
# keyed per-account so one caller can't drive up AI spend by hammering
# their own account from many IPs. See docs/concerns/README.md's now-fixed
# "No rate limiting on AI-backed routes" entry.
@rate_limiter_service.rate_limited(
    "career_knowledge_create", account_key_func=lambda kwargs: kwargs["current_user"]["email"]
)
async def create_career_knowledge_base(
    payload: CareerKnowledgeBaseCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Bootstraps the caller's knowledge base: AI structures `raw_input` into
    Markdown `content` (claude.md flow steps 1-4), then that content is
    embedded and indexed in Qdrant for later semantic search/retrieval.
    """
    user_id = await _current_user_id(current_user, db)

    if await career_knowledge_repository.get_by_user_id(user_id, db) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Career knowledge base already exists — use PUT to update it",
        )

    content = await _structure_or_502(payload.raw_input)
    entry = await career_knowledge_repository.create(user_id, payload.raw_input, content, db)

    await _reindex_best_effort(user_id, content)

    return entry


@router.get("/", response_model=CareerKnowledgeBaseRead)
async def get_my_career_knowledge_base(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    return await get_or_404(
        career_knowledge_repository.get_by_user_id(user_id, db), "Career knowledge base not found"
    )


@router.put("/", response_model=CareerKnowledgeBaseRead)
# Rate-limited the same as the create route above — a bare `content` edit
# (no AI call) is cheap, but PUT is the same endpoint the `raw_input`
# AI-restructuring path uses, so the whole route is protected uniformly
# rather than only when the request happens to include `raw_input`.
@rate_limiter_service.rate_limited(
    "career_knowledge_update", account_key_func=lambda kwargs: kwargs["current_user"]["email"]
)
async def update_my_career_knowledge_base(
    update_data: CareerKnowledgeBaseUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Two distinct edit paths sharing one endpoint (see
    CareerKnowledgeBaseUpdate's docstring): a fresh `raw_input` re-dump
    regenerates `content` via AI from scratch; a bare `content` edit is the
    user directly editing their Markdown (step 5), no AI involved. Either
    way, the resulting content is always re-indexed in Qdrant so search
    stays in sync with what's actually stored.
    """
    user_id = await _current_user_id(current_user, db)
    entry = await get_or_404(
        career_knowledge_repository.get_by_user_id(user_id, db), "Career knowledge base not found"
    )

    fields = update_data.model_dump(exclude_unset=True)
    if "raw_input" in fields:
        fields["content"] = await _structure_or_502(fields["raw_input"])

    updated = await career_knowledge_repository.update(entry, fields, db)
    await _reindex_best_effort(user_id, updated.content)

    return updated


@router.delete("/")
async def delete_my_career_knowledge_base(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    user_id = await _current_user_id(current_user, db)
    entry = await get_or_404(
        career_knowledge_repository.get_by_user_id(user_id, db), "Career knowledge base not found"
    )
    await career_knowledge_repository.delete(entry, db)
    await _delete_index_best_effort(user_id)
    return {"detail": "Career knowledge base deleted"}


@router.get("/search", response_model=list[CareerKnowledgeSearchResult])
async def search_my_career_knowledge_base(
    query: str = Query(min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(database.get_session),
):
    """
    Semantic search over the caller's own indexed knowledge base chunks.
    Scaffolding for Phase 2's job-description matching — exposed as its own
    endpoint now so retrieval can be verified independently of that later
    work.
    """
    user_id = await _current_user_id(current_user, db)
    try:
        results = await search_knowledge_base(user_id, query, top_k)
    except (AIIntegrationError, RetrievalError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return results
