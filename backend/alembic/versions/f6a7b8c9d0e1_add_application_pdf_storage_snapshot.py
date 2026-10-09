"""retain private object-storage identity for immutable application PDFs"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "f23456789012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application_records", sa.Column("pdf_storage_key_snapshot", sa.String(length=500), nullable=True))
    op.add_column("application_records", sa.Column("pdf_sha256_snapshot", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("application_records", "pdf_sha256_snapshot")
    op.drop_column("application_records", "pdf_storage_key_snapshot")
