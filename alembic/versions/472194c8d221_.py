"""empty message

Revision ID: 472194c8d221
Revises: 7b924fcc5267, add_products_table
Create Date: 2025-07-11 18:38:46.230551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '472194c8d221'
down_revision: Union[str, None] = ('7b924fcc5267', 'add_products_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
