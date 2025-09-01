from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'robust_sync_001'
# Правильный предыдущий revision из файла fix_wb_id_unique_constraint.py
down_revision = 'fix_wb_id_unique'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('feedbacks', sa.Column('wb_updated_at', sa.DateTime(), nullable=True))
    op.add_column('feedbacks', sa.Column('global_user_id', sa.String(), nullable=True))
    op.add_column('feedbacks', sa.Column('wb_user_id', sa.Integer(), nullable=True))
    op.add_column('feedbacks', sa.Column('content_hash', sa.String(), nullable=True))
    op.add_column('feedbacks', sa.Column('suspected_deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('feedbacks', sa.Column('superseded_by_wb_id', sa.String(), nullable=True))

    op.create_index('ix_feedbacks_global_user_id', 'feedbacks', ['global_user_id'], unique=False)
    op.create_index('ix_feedbacks_wb_user_id', 'feedbacks', ['wb_user_id'], unique=False)
    op.create_index('ix_feedbacks_content_hash', 'feedbacks', ['content_hash'], unique=False)
    op.create_index('idx_brand_article_global_user', 'feedbacks', ['brand', 'article', 'global_user_id'], unique=False)


def downgrade():
    op.drop_index('idx_brand_article_global_user', table_name='feedbacks')
    op.drop_index('ix_feedbacks_content_hash', table_name='feedbacks')
    op.drop_index('ix_feedbacks_wb_user_id', table_name='feedbacks')
    op.drop_index('ix_feedbacks_global_user_id', table_name='feedbacks')

    op.drop_column('feedbacks', 'superseded_by_wb_id')
    op.drop_column('feedbacks', 'suspected_deleted_at')
    op.drop_column('feedbacks', 'content_hash')
    op.drop_column('feedbacks', 'wb_user_id')
    op.drop_column('feedbacks', 'global_user_id')
    op.drop_column('feedbacks', 'wb_updated_at')


