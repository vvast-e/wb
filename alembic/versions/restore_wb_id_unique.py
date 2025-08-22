"""restore wb_id unique constraint

Revision ID: restore_wb_id_unique
Revises: fix_wb_id_unique_constraint
Create Date: 2024-01-15 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'restore_wb_id_unique'
down_revision = 'fix_wb_id_unique_constraint'
branch_labels = None
depends_on = None


def upgrade():
    # Убираем составное ограничение уникальности (wb_id, brand, user_id)
    op.drop_constraint('uq_feedbacks_wb_id_brand_user', 'feedbacks', type_='unique')
    
    # Возвращаем глобальное ограничение уникальности wb_id
    op.create_index('ix_feedbacks_wb_id', 'feedbacks', ['wb_id'], unique=True)


def downgrade():
    # Убираем глобальное ограничение уникальности wb_id
    op.drop_index('ix_feedbacks_wb_id', table_name='feedbacks')
    
    # Добавляем составное ограничение уникальности (wb_id, brand, user_id)
    op.create_unique_constraint('uq_feedbacks_wb_id_brand_user', 'feedbacks', ['wb_id', 'brand', 'user_id'])
