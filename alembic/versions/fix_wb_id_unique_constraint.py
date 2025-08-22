"""fix wb_id unique constraint

Revision ID: fix_wb_id_unique
Revises: add_vendor_code_to_feedbacks
Create Date: 2025-08-22 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_wb_id_unique'
down_revision = 'add_vendor_code_to_feedbacks'
branch_labels = None
depends_on = None


def upgrade():
    # Убираем глобальный уникальный индекс с wb_id
    op.drop_index('ix_feedbacks_wb_id', table_name='feedbacks')
    
    # Создаем обычный индекс для wb_id (без unique)
    op.create_index('ix_feedbacks_wb_id', 'feedbacks', ['wb_id'], unique=False)
    
    # Создаем составной уникальный индекс для wb_id + article + brand
    op.create_index('idx_wb_id_article_brand_unique', 'feedbacks', 
                   ['wb_id', 'article', 'brand'], unique=True)


def downgrade():
    # Убираем составной уникальный индекс
    op.drop_index('idx_wb_id_article_brand_unique', table_name='feedbacks')
    
    # Убираем обычный индекс
    op.drop_index('ix_feedbacks_wb_id', table_name='feedbacks')
    
    # Восстанавливаем глобальный уникальный индекс
    op.create_index('ix_feedbacks_wb_id', 'feedbacks', ['wb_id'], unique=True)

