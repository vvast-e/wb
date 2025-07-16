"""
add market to price_history

Revision ID: 493bdde06f57
Revises: 2fd81de6f86b
Create Date: 2024-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '493bdde06f57'
down_revision: Union[str, None] = '2fd81de6f86b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('price_history', sa.Column('market', sa.String(length=10), nullable=True, server_default='wb'))
    op.execute("UPDATE price_history SET market = 'wb' WHERE market IS NULL")
    op.alter_column('price_history', 'market', nullable=False)
    op.alter_column('price_history', 'market', server_default=None)

def downgrade() -> None:
    op.drop_column('price_history', 'market')
