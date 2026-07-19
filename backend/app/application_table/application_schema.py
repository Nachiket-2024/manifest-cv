from datetime import date, time, datetime
from pydantic import BaseModel, ConfigDict, Field

# Both are short, human-typed fields — a bound here is purely a sanity cap
# against a malformed/abusive request, not a real-world usage constraint.
_MAX_COMPANY_NAME_LENGTH = 200
_MAX_STATUS_LENGTH = 50


class ApplicationCreate(BaseModel):
    """
    Saves a tracked application from an already-finalized resume document
    (claude.md flow steps 19-23). `resume_draft_id` identifies which
    finalized document to snapshot — the actual content/PDF are copied
    server-side, never supplied directly by the client.
    """

    resume_draft_id: int
    company_name: str = Field(min_length=1, max_length=_MAX_COMPANY_NAME_LENGTH)
    application_date: date
    application_time: time | None = None
    status: str = Field(min_length=1, max_length=_MAX_STATUS_LENGTH)


class ApplicationUpdate(BaseModel):
    """
    Partial update. Deliberately excludes the resume content/PDF snapshot —
    those are read-only once saved (see ApplicationRecord's docstring);
    only the tracking fields (company/date/time/status) can change as an
    application progresses.
    """

    company_name: str | None = Field(default=None, min_length=1, max_length=_MAX_COMPANY_NAME_LENGTH)
    application_date: date | None = None
    application_time: time | None = None
    status: str | None = Field(default=None, min_length=1, max_length=_MAX_STATUS_LENGTH)


class ApplicationRead(BaseModel):
    """Summary schema for list views — excludes the resume content/PDF snapshot to stay lightweight."""

    id: int
    company_name: str
    application_date: date
    application_time: time | None
    status: str
    template_id_snapshot: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationDetailRead(ApplicationRead):
    """Full schema for a single application — includes the resume Markdown snapshot (not the PDF bytes)."""

    resume_content_snapshot: str
