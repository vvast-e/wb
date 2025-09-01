from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_bables_resolved_001'
down_revision = 'robust_sync_001'
branch_labels = None
depends_on = None


def upgrade():
    # Надёжно: дропаем колонки, если существуют (PostgreSQL IF EXISTS), затем добавляем новую
    op.execute('ALTER TABLE feedbacks DROP COLUMN IF EXISTS bables')
    op.execute('ALTER TABLE feedbacks DROP COLUMN IF EXISTS reasons')
    op.add_column('feedbacks', sa.Column('bables_resolved', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('feedbacks', 'bables_resolved')
    op.add_column('feedbacks', sa.Column('bables', sa.JSON(), nullable=True))
    op.add_column('feedbacks', sa.Column('reasons', sa.JSON(), nullable=True))


