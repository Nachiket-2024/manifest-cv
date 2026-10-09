"""merge the upstream sync and capability-name migration heads

Revision ID: d4e5f6a7b8c9
Revises: b71159159522, c2d3e4f5a6b7
Create Date: 2026-09-29 00:00:00.000000
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = ("b71159159522", "c2d3e4f5a6b7")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
