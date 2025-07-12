"""add telegram_users table

Revision ID: add_telegram_users_table
Revises: add_products_table
Create Date: 2024-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_telegram_users_table'
down_revision: Union[str, None] = 'add_products_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'telegram_users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('telegram_id', sa.Integer(), unique=True, index=True, nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('telegram_users') 