from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

# Generous enough for a genuinely long multi-page resume/LinkedIn/GitHub
# text dump, but bounded — without a cap, an oversized raw_input would be
# sent wholesale into a Gemini prompt (real cost, possible provider-side
# rejection) and balloon storage in a TEXT column with no other limit.
_MAX_TEXT_LENGTH = 50_000


class CareerKnowledgeBaseCreate(BaseModel):
    """
    Bootstraps a user's knowledge base from their initial raw text dump
    (claude.md flow step 1). `content` is generated from `raw_input` by
    ai_integration.gemini_client.structure_knowledge_base (steps 2-3) —
    see career_knowledge_routes.py.
    """

    raw_input: str = Field(min_length=1, max_length=_MAX_TEXT_LENGTH)


class CareerKnowledgeBaseUpdate(BaseModel):
    """
    Partial update. Supplying `raw_input` re-dumps and regenerates `content`
    from scratch via AI (discarding any manual edits to the old `content`).
    Supplying `content` alone is the user directly editing their structured
    knowledge base (step 5) — no AI call involved. If both are supplied,
    `raw_input` wins: see career_knowledge_routes.py.
    """

    raw_input: str | None = Field(default=None, min_length=1, max_length=_MAX_TEXT_LENGTH)
    content: str | None = Field(default=None, min_length=1, max_length=_MAX_TEXT_LENGTH)


class CareerKnowledgeBaseRead(BaseModel):
    """Schema returned in API responses."""

    id: int
    raw_input: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CareerKnowledgeSearchResult(BaseModel):
    """One semantically-matched chunk from a user's own knowledge base
    (see retrieval/knowledge_retrieval_service.py's chunk_markdown)."""

    chunk: str
    score: float
