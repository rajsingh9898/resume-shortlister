"""add_candidate_confidence

Revision ID: 98973029cf2a
Revises: fb2e2b863cb3
Create Date: 2026-07-25 00:16:17.372836

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98973029cf2a'
down_revision: Union[str, Sequence[str], None] = 'fb2e2b863cb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add experience_confidence and degrees_confidence with server default of 1.0
    op.add_column('candidates', sa.Column('experience_confidence', sa.Float(), nullable=False, server_default=sa.text('1.0')))
    op.add_column('candidates', sa.Column('degrees_confidence', sa.Float(), nullable=False, server_default=sa.text('1.0')))


def downgrade() -> None:
    op.drop_column('candidates', 'experience_confidence')
    op.drop_column('candidates', 'degrees_confidence')
