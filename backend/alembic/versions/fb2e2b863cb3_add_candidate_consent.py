"""add_candidate_consent

Revision ID: fb2e2b863cb3
Revises: 0e49c36d4b40
Create Date: 2026-07-24 23:52:45.652014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb2e2b863cb3'
down_revision: Union[str, Sequence[str], None] = '0e49c36d4b40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add consent_given column to candidates table with default True (1)
    op.add_column('candidates', sa.Column('consent_given', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade() -> None:
    # Drop column from candidates table
    op.drop_column('candidates', 'consent_given')
