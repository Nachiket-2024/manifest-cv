from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String, LargeBinary
from sqlalchemy.sql import func

from ..database.base import Base


class ResumeDocument(Base):
    """
    The finalized, compiled PDF for one approved resume draft (claude.md
    Phase 3, flow steps 14-18). One per draft (unique resume_draft_id) —
    re-finalizing with a different template overwrites the previous one
    rather than accumulating history, since only the current selection
    matters until the user saves an application (at which point
    ApplicationRecord copies a snapshot that outlives this row — see
    application_table/application_model.py).
    """

    __tablename__ = "resume_documents"

    id = Column(Integer, primary_key=True, index=True)

    resume_draft_id = Column(
        Integer, ForeignKey("resume_drafts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    template_id = Column(String, nullable=False)
    tex_source = Column(Text, nullable=False)
    pdf_bytes = Column(LargeBinary, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
