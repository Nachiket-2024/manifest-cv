import importlib
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from mystic_auth.database.base import Base
else:
    root = __package__.split(".")[0] if __package__ else "app"
    Base = importlib.import_module(f"{'backend.' if root == 'backend' else ''}mystic_auth.database.base").Base


class ResumeWorkspace(Base):
    __tablename__ = "resume_workspaces"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    job_description = Column(Text, nullable=False)
    template_key = Column(String(80), nullable=False, server_default="classic_single_column")
    status = Column(String(30), nullable=False, server_default="draft")
    current_revision_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ResumeRevision(Base):
    __tablename__ = "resume_revisions"
    __table_args__ = (UniqueConstraint("workspace_id", "revision_number", name="uq_resume_revision_number"),)
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("resume_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False)
    document_json = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    change_kind = Column(String(30), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
