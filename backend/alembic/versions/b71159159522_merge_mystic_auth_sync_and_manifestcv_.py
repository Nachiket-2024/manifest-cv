"""merge mystic-auth sync and ManifestCV migration heads

Revision ID: b71159159522
Revises: 6d6c9f178682, d62c136d1c6c
Create Date: 2026-09-06 00:00:00.000000

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "b71159159522"
down_revision: str | Sequence[str] | None = ("6d6c9f178682", "d62c136d1c6c")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
