import importlib
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from mystic_auth.database.base import Base
else:
    root = __package__.split(".")[0] if __package__ else "app"
    Base = importlib.import_module(f"{'backend.' if root == 'backend' else ''}mystic_auth.database.base").Base


class ResumeJob(Base):
    __tablename__ = "resume_jobs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("resume_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, server_default="queued")
    result_revision_id = Column(Integer, ForeignKey("resume_revisions.id", ondelete="SET NULL"), nullable=True)
    error_code = Column(String(80), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
