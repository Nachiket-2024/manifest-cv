"""store structured builder references on application snapshots"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "f01234567890"
down_revision: str | Sequence[str] | None = "ef1234567890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application_records", sa.Column("resume_workspace_id", sa.Integer(), nullable=True))
    op.add_column("application_records", sa.Column("resume_revision_id", sa.Integer(), nullable=True))
    op.add_column("application_records", sa.Column("document_snapshot", sa.Text(), nullable=True))
    op.create_foreign_key("fk_application_workspace", "application_records", "resume_workspaces", ["resume_workspace_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_application_revision", "application_records", "resume_revisions", ["resume_revision_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_application_records_resume_workspace_id", "application_records", ["resume_workspace_id"])
    op.create_index("ix_application_records_resume_revision_id", "application_records", ["resume_revision_id"])


def downgrade() -> None:
    op.drop_index("ix_application_records_resume_revision_id", table_name="application_records")
    op.drop_index("ix_application_records_resume_workspace_id", table_name="application_records")
    op.drop_constraint("fk_application_revision", "application_records", type_="foreignkey")
    op.drop_constraint("fk_application_workspace", "application_records", type_="foreignkey")
    op.drop_column("application_records", "document_snapshot")
    op.drop_column("application_records", "resume_revision_id")
    op.drop_column("application_records", "resume_workspace_id")
