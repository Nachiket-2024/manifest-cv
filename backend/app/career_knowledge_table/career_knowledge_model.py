import importlib
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
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


class CareerKnowledgeBase(Base):
    """
    One row per user: their single-source-of-truth career knowledge base.
    `raw_input` is the text dump the user pastes in (resume text, LinkedIn,
    GitHub, projects, experience, achievements, skills, notes); `content`
    is the well-structured Markdown knowledge base built from it by AI,
    and always directly user-editable afterward.

    Kept as exactly one row per user (unique user_id) rather than many
    entries: this is the single source of truth for all of a user's
    career information, not a collection of separate notes.
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
