"""add wb_ip to feedback

Revision ID: bb4122d77411
Revises: e3bdeb4650cc
Create Date: 2025-07-23 04:15:15.959748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb4122d77411'
down_revision: Union[str, None] = 'e3bdeb4650cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
