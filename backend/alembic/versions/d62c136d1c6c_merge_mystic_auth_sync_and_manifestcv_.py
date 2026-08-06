"""merge mystic-auth sync and ManifestCV migration heads

Revision ID: d62c136d1c6c
Revises: d6e7f8a9b0c1, f5a6b7c8d9e0
Create Date: 2026-08-05 12:15:06.622987

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d62c136d1c6c"
down_revision: str | Sequence[str] | None = ("d6e7f8a9b0c1", "f5a6b7c8d9e0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
