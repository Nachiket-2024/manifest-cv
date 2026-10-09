"""merge MysticAuth token revocation and ManifestCV resume branches

Revision ID: f9a0b1c2d3e4
Revises: a7b8c9d0e1f2, f8b9c0d1e2f3
"""

revision: str = "f9a0b1c2d3e4"
down_revision: str | tuple[str, str] | None = ("a7b8c9d0e1f2", "f8b9c0d1e2f3")
branch_labels: str | tuple[str, str] | None = None
depends_on: str | tuple[str, str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
