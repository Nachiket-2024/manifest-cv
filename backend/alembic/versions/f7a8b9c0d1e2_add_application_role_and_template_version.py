"""add application role and template version snapshot metadata"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "f7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application_records", sa.Column("role", sa.String(length=200), nullable=True))
    op.add_column("application_records", sa.Column("template_version_snapshot", sa.String(length=80), nullable=True))
    op.execute("UPDATE application_records SET template_version_snapshot = '1' WHERE template_version_snapshot IS NULL")


def downgrade() -> None:
    op.drop_column("application_records", "template_version_snapshot")
    op.drop_column("application_records", "role")
