"""string

Revision ID: 72a5705c3c6c
Revises: 493bdde06f57
Create Date: 2025-07-16 18:26:18.123895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72a5705c3c6c'
down_revision: Union[str, None] = '493bdde06f57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
