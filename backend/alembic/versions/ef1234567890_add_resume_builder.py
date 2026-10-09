"""add structured resume builder workspaces and revisions"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "ef1234567890"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("resume_workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False), sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False), sa.Column("current_revision_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_workspaces_user_id", "resume_workspaces", ["user_id"])
    op.create_table("resume_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("resume_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False), sa.Column("document_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False), sa.Column("change_kind", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "revision_number", name="uq_resume_revision_number"),
    )
    op.create_index("ix_resume_revisions_workspace_id", "resume_revisions", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_revisions_workspace_id", table_name="resume_revisions")
    op.drop_table("resume_revisions")
    op.drop_index("ix_resume_workspaces_user_id", table_name="resume_workspaces")
    op.drop_table("resume_workspaces")
