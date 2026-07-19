"""add resume documents

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-16 00:00:02.000000

The finalized, compiled PDF for one approved resume draft — one per draft,
re-finalizing with a different template overwrites the previous row rather
than accumulating history (see resume_document_table/resume_document_model.py).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'resume_documents',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('resume_draft_id', sa.Integer(), sa.ForeignKey('resume_drafts.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('template_id', sa.String(), nullable=False),
        sa.Column('tex_source', sa.Text(), nullable=False),
        sa.Column('pdf_bytes', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('resume_documents')
