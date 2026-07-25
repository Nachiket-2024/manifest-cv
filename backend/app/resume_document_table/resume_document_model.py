import importlib
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text
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


class ResumeDocument(Base):
    """
    The finalized, compiled PDF for one approved resume draft. One per
    draft (unique resume_draft_id) —
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
