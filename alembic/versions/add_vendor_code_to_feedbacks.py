"""add vendor_code to feedbacks

Revision ID: add_vendor_code_to_feedbacks
Revises: add_platform_to_shops
Create Date: 2025-01-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_vendor_code_to_feedbacks'
down_revision = 'add_platform_to_shops'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поле vendor_code в таблицу feedbacks
    op.add_column('feedbacks', sa.Column('vendor_code', sa.String(), nullable=True))
    
    # Создаем индекс для быстрого поиска по vendor_code
    op.create_index('ix_feedbacks_vendor_code', 'feedbacks', ['vendor_code'])


def downgrade():
    # Удаляем индекс
    op.drop_index('ix_feedbacks_vendor_code', table_name='feedbacks')
    
    # Удаляем поле vendor_code
    op.drop_column('feedbacks', 'vendor_code')

