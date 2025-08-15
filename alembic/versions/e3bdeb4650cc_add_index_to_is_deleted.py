"""add_index_to_is_deleted

Revision ID: e3bdeb4650cc
Revises: a4adc8b72956
Create Date: 2025-07-23 03:59:21.510446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3bdeb4650cc'
down_revision: Union[str, None] = 'a4adc8b72956'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
