"""add products table

Revision ID: add_products_table
Revises: 0028d4b6fc25
Create Date: 2024-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_products_table'
down_revision: Union[str, None] = '0028d4b6fc25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('nm_id', sa.Integer(), unique=True, index=True, nullable=False),
        sa.Column('vendor_code', sa.String(), index=True, nullable=True),
        sa.Column('brand', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table('products') 