"""Merge heads before adding deleted_at

Revision ID: 6faef9c12b2e
Revises: 90d8fc475493, add_price_change_history_table
Create Date: 2025-07-12 19:22:07.447704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6faef9c12b2e'
down_revision: Union[str, None] = ('90d8fc475493', 'add_price_change_history_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
