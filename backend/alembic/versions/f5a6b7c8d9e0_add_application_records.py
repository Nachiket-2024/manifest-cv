"""add application records

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-16 00:00:03.000000

A tracked job application — a fully self-contained snapshot of the resume
actually sent, copied at save time rather than referencing the source draft/
document by foreign key, so it survives the user later editing or deleting
either of those (see application_table/application_model.py).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'application_records',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('application_date', sa.Date(), nullable=False),
        sa.Column('application_time', sa.Time(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('resume_content_snapshot', sa.Text(), nullable=False),
        sa.Column('template_id_snapshot', sa.String(), nullable=False),
        sa.Column('pdf_snapshot', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('application_records')
