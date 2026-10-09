"""merge MysticAuth lifecycle and ManifestCV migration heads

Revision ID: b8c9d0e1f2a3
Revises: f4a1c2e8b7d6, f9a0b1c2d3e4
"""

from collections.abc import Sequence

revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = ("f4a1c2e8b7d6", "f9a0b1c2d3e4")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
