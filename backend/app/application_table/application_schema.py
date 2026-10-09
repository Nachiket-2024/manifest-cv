from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# The only statuses the frontend's status selector (ApplicationsPage.tsx's
# STATUS_OPTIONS) ever sends. Constraining the backend to the same fixed
# set closes an input-validation gap (arbitrary free text was previously
# accepted and stored) without dropping any behavior the UI actually uses.
# Extending this set to add a new status (e.g. "withdrawn") means updating
# both this Literal and STATUS_OPTIONS together.
ApplicationStatus = Literal["applied", "interviewing", "offered", "rejected"]

# A short, human-typed field. A bound here is purely a sanity cap against a
# malformed/abusive request, not a real-world usage constraint.
_MAX_COMPANY_NAME_LENGTH = 200


class ApplicationCreate(BaseModel):
    """
    Saves a tracked application from an approved Resume Studio workspace.
    The actual content and PDF are copied server-side, never supplied by the
    client.
    """

    workspace_id: int
    company_name: str = Field(min_length=1, max_length=_MAX_COMPANY_NAME_LENGTH)
    role: str | None = Field(default=None, max_length=200)
    application_date: date
    application_time: time | None = None
    status: ApplicationStatus

class ApplicationUpdate(BaseModel):
    """
    Partial update. Deliberately excludes the resume content/PDF snapshot,
    read-only once saved (see ApplicationRecord's docstring). Only the
    tracking fields (company/date/time/status) can change as an
    application progresses.
    """

    company_name: str | None = Field(default=None, min_length=1, max_length=_MAX_COMPANY_NAME_LENGTH)
    application_date: date | None = None
    application_time: time | None = None
    status: ApplicationStatus | None = None


class ApplicationRead(BaseModel):
    """Summary schema for list views. Excludes the resume content/PDF snapshot to stay lightweight."""

    id: int
    company_name: str
    role: str | None
    application_date: date
    application_time: time | None
    status: ApplicationStatus
    template_id_snapshot: str
    created_at: datetime
    updated_at: datetime
    resume_workspace_id: int | None = None
    resume_revision_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationDetailRead(ApplicationRead):
    """Full schema for a single application. Includes the resume Markdown snapshot (not the PDF bytes)."""

    resume_content_snapshot: str
    document_snapshot: str | None = None
    pdf_storage_key_snapshot: str | None = None
    pdf_sha256_snapshot: str | None = None
