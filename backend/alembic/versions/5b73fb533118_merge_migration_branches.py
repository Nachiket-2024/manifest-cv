"""merge migration branches

Revision ID: 5b73fb533118
Revises: b8c9d0e1f2a3, f6c7d8e9a0b1
Create Date: 2026-10-12 00:56:45.298600

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '5b73fb533118'
down_revision: str | Sequence[str] | None = ('b8c9d0e1f2a3', 'f6c7d8e9a0b1')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    return None


def downgrade() -> None:
    """Downgrade schema."""
    return None
