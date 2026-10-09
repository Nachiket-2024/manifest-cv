import importlib
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, Time
from sqlalchemy.sql import func

if TYPE_CHECKING:
    # mypy can't follow the dynamic import below, so it gets a normal,
    # statically-resolvable import instead. Never executed at runtime,
    # since TYPE_CHECKING is always False when the module actually runs.
    from mystic_auth.database.base import Base
else:
    # `mystic_auth` is a sibling package of `app`, not a child of it, so a
    # relative import can't reach it, and a bare absolute import only resolves
    # under Docker (WORKDIR=backend). The repo-root test suite instead imports
    # this module as `backend.app...`, where only `backend.mystic_auth` is
    # importable. Deriving the prefix from __package__ (same trick as
    # app/sdk.py) keeps this working in both contexts and resolves to the
    # exact same declarative Base/metadata registry either way. Critical here
    # specifically, since SQLAlchemy's table registration depends on every
    # model subclassing the identical Base object.
    _pkg_root = __package__.split(".")[0] if __package__ else "app"
    _mystic_auth_root = "backend.mystic_auth" if _pkg_root == "backend" else "mystic_auth"
    Base = importlib.import_module(f"{_mystic_auth_root}.database.base").Base


class ApplicationRecord(Base):
    """
    A tracked job application. Fully self-contained snapshot of the resume
    actually sent, copied at save time from the approved Resume Studio revision
    that produced it rather than referencing them by foreign key. This is
    deliberate: a tracked application must survive the user later editing
    or deleting the workspace revision it came from, unlike CareerKnowledgeBase,
    which has no meaning without its owner and so cascades instead. This
    data's whole purpose is outliving its source.

    `status` (one of ApplicationStatus's fixed set: applied/interviewing/
    offered/rejected, see application_schema.py) and the identifying fields
    are the only parts a user can update after saving. The resume
    content/PDF snapshot itself is read-only once created.
    """

    __tablename__ = "application_records"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    company_name = Column(String, nullable=False)
    role = Column(String(200), nullable=True)
    application_date = Column(Date, nullable=False)
    application_time = Column(Time, nullable=True)
    status = Column(String, nullable=False)

    resume_content_snapshot = Column(Text, nullable=False)
    template_id_snapshot = Column(String, nullable=False)
    template_version_snapshot = Column(String(80), nullable=True)
    pdf_snapshot = Column(LargeBinary, nullable=False)
    resume_workspace_id = Column(Integer, ForeignKey("resume_workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    resume_revision_id = Column(Integer, ForeignKey("resume_revisions.id", ondelete="SET NULL"), nullable=True, index=True)
    document_snapshot = Column(Text, nullable=True)
    pdf_storage_key_snapshot = Column(String(500), nullable=True)
    pdf_sha256_snapshot = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
