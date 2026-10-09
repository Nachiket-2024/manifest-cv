"""Store the selected resume template on each workspace."""

import sqlalchemy as sa

from alembic import op

revision = "f8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resume_workspaces",
        sa.Column("template_key", sa.String(length=80), nullable=True),
    )
    op.execute("UPDATE resume_workspaces SET template_key = 'classic_single_column' WHERE template_key IS NULL")
    op.alter_column("resume_workspaces", "template_key", nullable=False, server_default="classic_single_column")


def downgrade() -> None:
    op.drop_column("resume_workspaces", "template_key")
