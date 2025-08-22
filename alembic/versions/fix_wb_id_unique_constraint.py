"""fix wb_id unique constraint

Revision ID: fix_wb_id_unique_constraint
Revises: add_platform_to_shops
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_wb_id_unique_constraint'
down_revision = 'add_platform_to_shops'
branch_labels = None
depends_on = None


def upgrade():
    # Убираем глобальное ограничение уникальности wb_id
    op.drop_index('ix_feedbacks_wb_id', table_name='feedbacks')
    
    # Добавляем составное ограничение уникальности (wb_id, brand, user_id)
    op.create_unique_constraint('uq_feedbacks_wb_id_brand_user', 'feedbacks', ['wb_id', 'brand', 'user_id'])


def downgrade():
    # Возвращаем глобальное ограничение уникальности wb_id
    op.drop_constraint('uq_feedbacks_wb_id_brand_user', 'feedbacks', type_='unique')
    
    # Восстанавливаем простой индекс для wb_id
    op.create_index('ix_feedbacks_wb_id', 'feedbacks', ['wb_id'], unique=True)
