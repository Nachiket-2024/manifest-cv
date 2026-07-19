from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from ..database.base import Base


class ResumeDraft(Base):
    """
    A tailored resume in progress for one job description (claude.md's
    Application Flow steps 6-13). Many per user — unlike CareerKnowledgeBase,
    which is a single source of truth, a user tailors a separate resume per
    job they're applying to.

    `resume_content` starts null until the first AI generation (step 8) and
    is then either directly edited or regenerated via `refinement_prompt`
    (steps 9-12) until the user approves (step 13, `status` -> "approved").
    Approved drafts are content-locked (see resume_routes.py) — only
    template selection/finalization (Phase 3) may proceed from there.
    """

    __tablename__ = "resume_drafts"

    id = Column(Integer, primary_key=True, index=True)

    # Many drafts per user — cascades on account deletion since a draft has
    # no meaning without its owning account.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    job_description = Column(Text, nullable=False)
    resume_content = Column(Text, nullable=True)

    # "draft" | "approved" — plain string rather than a DB enum, matching
    # this codebase's existing preference for permissive string status
    # columns (e.g. application status in this same feature) over a rigid
    # DB-level enum that needs a migration to extend.
    status = Column(String, nullable=False, server_default="draft")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
