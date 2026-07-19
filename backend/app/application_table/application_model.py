from sqlalchemy import Column, Integer, Text, DateTime, Date, Time, ForeignKey, String, LargeBinary
from sqlalchemy.sql import func

from ..database.base import Base


class ApplicationRecord(Base):
    """
    A tracked job application (claude.md flow steps 19-23) — fully
    self-contained snapshot of the resume actually sent, copied at save
    time from the ResumeDraft/ResumeDocument that produced it rather than
    referencing them by foreign key. This is deliberate: claude.md calls
    this "the resume snapshot", and a tracked application must survive the
    user later editing or deleting the draft/document it came from (unlike
    CareerKnowledgeBase, which has no meaning without its owner and so
    cascades instead — this data's whole purpose is outliving its source).

    `status` (applied/interviewing/offered/rejected/etc, claude.md's list is
    non-exhaustive) and the identifying fields are the only parts a user
    can update after saving — the resume content/PDF snapshot itself is
    read-only once created.
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
