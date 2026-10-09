"""store immutable resume render artifact metadata"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "f12345678901"
down_revision: str | Sequence[str] | None = "f01234567890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("resume_render_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision_id", sa.Integer(), sa.ForeignKey("resume_revisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=100), nullable=False), sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False), sa.Column("status", sa.String(length=20), server_default="succeeded", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_render_artifacts_revision_id", "resume_render_artifacts", ["revision_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_render_artifacts_revision_id", table_name="resume_render_artifacts")
    op.drop_table("resume_render_artifacts")
