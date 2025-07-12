"""add price_change_history table

Revision ID: add_price_change_history_table
Revises: add_telegram_users_table
Create Date: 2024-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_price_change_history_table'
down_revision: Union[str, None] = 'add_telegram_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'price_change_history',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('nm_id', sa.Integer(), index=True, nullable=False),
        sa.Column('shop_id', sa.Integer(), index=True, nullable=True),
        sa.Column('change_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('price_change_history') 