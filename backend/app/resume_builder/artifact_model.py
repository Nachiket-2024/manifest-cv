import importlib
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from mystic_auth.database.base import Base
else:
    root = __package__.split(".")[0] if __package__ else "app"
    Base = importlib.import_module(f"{'backend.' if root == 'backend' else ''}mystic_auth.database.base").Base


class ResumeRenderArtifact(Base):
    __tablename__ = "resume_render_artifacts"
    id = Column(Integer, primary_key=True)
    revision_id = Column(Integer, ForeignKey("resume_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False, unique=True)
    content_type = Column(String(100), nullable=False)
    byte_size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, server_default="succeeded")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
