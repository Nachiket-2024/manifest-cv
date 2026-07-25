import importlib
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

if TYPE_CHECKING:
    # mypy can't follow the dynamic import below, so it gets a normal,
    # statically-resolvable import instead — never executed at runtime,
    # since TYPE_CHECKING is always False when the module actually runs.
    from mystic_auth.database.base import Base
else:
    # See application_table/application_model.py's identical import for the
    # full dual-context reasoning (same trick as app/sdk.py).
    _pkg_root = __package__.split(".")[0] if __package__ else "app"
    _mystic_auth_root = "backend.mystic_auth" if _pkg_root == "backend" else "mystic_auth"
    Base = importlib.import_module(f"{_mystic_auth_root}.database.base").Base


class ResumeDraft(Base):
    """
    A tailored resume in progress for one job description. Many per user —
    unlike CareerKnowledgeBase, which is a single source of truth, a user
    tailors a separate resume per job they're applying to.

    `resume_content` starts null until the first AI generation and is then
    either directly edited or regenerated via `refinement_prompt` until the
    user approves (`status` -> "approved"). Approved drafts are
    content-locked (see resume_routes.py) — only template
    selection/finalization may proceed from there.
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
