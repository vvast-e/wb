"""add wb_ip to feedback

Revision ID: 0f003ce7ba2d
Revises: bb4122d77411
Create Date: 2025-07-23 04:21:30.836527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f003ce7ba2d'
down_revision: Union[str, None] = 'bb4122d77411'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('feedbacks', sa.Column('wb_id', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    pass
