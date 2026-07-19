from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from ..database.base import Base


class CareerKnowledgeBase(Base):
    """
    One row per user: their single-source-of-truth career knowledge base
    (see claude.md's Application Flow steps 1-5). `raw_input` is the text
    dump the user pastes in (resume text, LinkedIn, GitHub, projects,
    experience, achievements, skills, notes); `content` is the
    well-structured Markdown knowledge base built from it — mechanically
    equal to raw_input for now (Phase 1, CRUD only), reorganized by AI in
    Phase 1.5, and always directly user-editable afterward (step 5).

    Kept as exactly one row per user (unique user_id) rather than many
    entries: claude.md is explicit that this is "the single source of truth
    for all career information", not a collection of separate notes.
    """

    __tablename__ = "career_knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)

    # One knowledge base per user; cascades on account deletion since this
    # data has no meaning without its owning account.
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    raw_input = Column(Text, nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
