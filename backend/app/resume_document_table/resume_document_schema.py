from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class ResumeDocumentFinalize(BaseModel):
    """Selects which template to compile the approved resume with (claude.md flow step 17)."""

    template_id: str = Field(min_length=1)


class ResumeDocumentRead(BaseModel):
    """
    Metadata for a finalized document. `pdf_bytes`/`tex_source` are
    deliberately excluded — fetched separately via the download endpoint so
    this stays cheap to return alongside a resume draft.
    """

    id: int
    resume_draft_id: int
    template_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateInfo(BaseModel):
    id: str
    label: str
