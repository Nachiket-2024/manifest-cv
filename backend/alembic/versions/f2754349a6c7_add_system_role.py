"""add system role

Revision ID: f2754349a6c7
Revises: f45a54f398cb
Create Date: 2026-04-11 11:50:11.593430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2754349a6c7'
down_revision: Union[str, Sequence[str], None] = 'f45a54f398cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.
    Adds new role 'system' to existing PostgreSQL enum type.
    """
    # Add new enum value safely (PostgreSQL requires ALTER TYPE)
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'system'")


def downgrade() -> None:
    """
    Downgrade schema.
    NOTE: PostgreSQL does NOT support removing enum values easily.
    """
    # No safe downgrade for enum removal in Postgres
    pass