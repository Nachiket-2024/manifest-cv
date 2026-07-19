from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

# See career_knowledge_table/career_knowledge_schema.py's _MAX_TEXT_LENGTH
# for the same "generous but bounded" reasoning — job postings and full
# resume drafts are both well within this; a refinement instruction is a
# short one-line request, hence its own much smaller cap below.
_MAX_TEXT_LENGTH = 50_000
_MAX_REFINEMENT_PROMPT_LENGTH = 2_000


class ResumeDraftCreate(BaseModel):
    """
    Starts a new tailored resume for a job description (claude.md flow step
    6). The AI-generated `resume_content` (steps 7-8) is produced by
    resume_routes.py from the caller's own knowledge base — never supplied
    directly by the client.
    """

    job_description: str = Field(min_length=1, max_length=_MAX_TEXT_LENGTH)


class ResumeDraftUpdate(BaseModel):
    """
    Two distinct edit paths sharing one endpoint (mirrors
    CareerKnowledgeBaseUpdate): a `refinement_prompt` regenerates
    `resume_content` via AI, re-matching the knowledge base against the
    prompt (steps 10-11) while discarding anything not already in it.
    Supplying `content` alone is a direct manual edit (step 9) — no AI call.
    If both are supplied, `refinement_prompt` wins: see resume_routes.py.
    """

    refinement_prompt: str | None = Field(default=None, min_length=1, max_length=_MAX_REFINEMENT_PROMPT_LENGTH)
    content: str | None = Field(default=None, min_length=1, max_length=_MAX_TEXT_LENGTH)


class ResumeDraftRead(BaseModel):
    """Schema returned in API responses."""

    id: int
    job_description: str
    resume_content: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
