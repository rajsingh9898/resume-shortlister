"""add_auth_fields

Revision ID: 0e49c36d4b40
Revises: 26cb127efac5
Create Date: 2026-07-23 09:33:07.734001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e49c36d4b40'
down_revision: Union[str, Sequence[str], None] = '26cb127efac5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add hashed_password and role columns to users table
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('users', sa.Column('role', sa.String(length=50), nullable=False, server_default='Recruiter'))


def downgrade() -> None:
    # Drop columns from users table
    op.drop_column('users', 'role')
    op.drop_column('users', 'hashed_password')
