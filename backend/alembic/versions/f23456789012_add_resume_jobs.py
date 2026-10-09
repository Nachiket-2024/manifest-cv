"""persist resume generation and refinement job state"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "f23456789012"
down_revision: str | Sequence[str] | None = "f12345678901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("resume_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("resume_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False), sa.Column("status", sa.String(length=20), server_default="queued", nullable=False),
        sa.Column("result_revision_id", sa.Integer(), sa.ForeignKey("resume_revisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True), sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_jobs_user_id", "resume_jobs", ["user_id"])
    op.create_index("ix_resume_jobs_workspace_id", "resume_jobs", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_jobs_workspace_id", table_name="resume_jobs")
    op.drop_index("ix_resume_jobs_user_id", table_name="resume_jobs")
    op.drop_table("resume_jobs")
