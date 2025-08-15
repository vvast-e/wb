"""change article to String(32) in feedbacks and feedback_analytics

Revision ID: 11282254ebeb
Revises: 7b36db38016d
Create Date: 2025-08-06 13:12:09.080992

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11282254ebeb'
down_revision: Union[str, None] = '7b36db38016d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
