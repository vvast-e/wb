"""change article to String(32) in feedbacks and feedback_analytics

Revision ID: 7b36db38016d
Revises: 0f003ce7ba2d
Create Date: 2025-08-06 13:09:01.879094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b36db38016d'
down_revision: Union[str, None] = '0f003ce7ba2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('feedbacks', 'article',
        existing_type=sa.INTEGER(),
        type_=sa.String(length=32),
        existing_nullable=False)
    op.alter_column('feedback_analytics', 'article',
        existing_type=sa.INTEGER(),
        type_=sa.String(length=32),
        existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('feedbacks', 'article',
        existing_type=sa.String(length=32),
        type_=sa.INTEGER(),
        existing_nullable=False)
    op.alter_column('feedback_analytics', 'article',
        existing_type=sa.String(length=32),
        type_=sa.INTEGER(),
        existing_nullable=False)
