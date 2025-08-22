"""add platform to shops

Revision ID: add_platform_to_shops
Revises: 28a729b6346d
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_platform_to_shops'
down_revision = '28a729b6346d'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поле platform
    op.add_column('shops', sa.Column('platform', sa.String(10), nullable=False, server_default='wb'))
    
    # Делаем поле name nullable
    op.alter_column('shops', 'name', nullable=True)
    
    # Делаем поле wb_name nullable
    op.alter_column('shops', 'wb_name', nullable=True)


def downgrade():
    # Убираем поле platform
    op.drop_column('shops', 'platform')
    
    # Возвращаем поле name как not nullable
    op.alter_column('shops', 'name', nullable=False)
    
    # Возвращаем поле wb_name как not nullable
    op.alter_column('shops', 'wb_name', nullable=False)
