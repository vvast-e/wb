"""stringnew 

Revision ID: a19f9515c69b
Revises: 72a5705c3c6c
Create Date: 2025-07-16 18:36:37.936794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a19f9515c69b'
down_revision: Union[str, None] = '72a5705c3c6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
