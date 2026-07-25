import importlib
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, Time
from sqlalchemy.sql import func

if TYPE_CHECKING:
    # mypy can't follow the dynamic import below, so it gets a normal,
    # statically-resolvable import instead — never executed at runtime,
    # since TYPE_CHECKING is always False when the module actually runs.
    from mystic_auth.database.base import Base
else:
    # `mystic_auth` is a sibling package of `app`, not a child of it, so a
    # relative import can't reach it, and a bare absolute import only resolves
    # under Docker (WORKDIR=backend); the repo-root test suite instead imports
    # this module as `backend.app...`, where only `backend.mystic_auth` is
    # importable. Deriving the prefix from __package__ (same trick as
    # app/sdk.py) keeps this working in both contexts and resolves to the
    # exact same declarative Base/metadata registry either way — critical here
    # specifically, since SQLAlchemy's table registration depends on every
    # model subclassing the identical Base object.
    _pkg_root = __package__.split(".")[0] if __package__ else "app"
    _mystic_auth_root = "backend.mystic_auth" if _pkg_root == "backend" else "mystic_auth"
    Base = importlib.import_module(f"{_mystic_auth_root}.database.base").Base


class ApplicationRecord(Base):
    """
    A tracked job application — fully self-contained snapshot of the
    resume actually sent, copied at save time from the
    ResumeDraft/ResumeDocument that produced it rather than referencing
    them by foreign key. This is deliberate: a tracked application must
    survive the user later editing or deleting the draft/document it came
    from (unlike
    CareerKnowledgeBase, which has no meaning without its owner and so
    cascades instead — this data's whole purpose is outliving its source).

    `status` (one of ApplicationStatus's fixed set — applied/interviewing/
    offered/rejected, see application_schema.py) and the identifying fields
    are the only parts a user can update after saving — the resume
    content/PDF snapshot itself is read-only once created.
    """

    __tablename__ = "application_records"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    company_name = Column(String, nullable=False)
    application_date = Column(Date, nullable=False)
    application_time = Column(Time, nullable=True)
    status = Column(String, nullable=False)

    resume_content_snapshot = Column(Text, nullable=False)
    template_id_snapshot = Column(String, nullable=False)
    pdf_snapshot = Column(LargeBinary, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
