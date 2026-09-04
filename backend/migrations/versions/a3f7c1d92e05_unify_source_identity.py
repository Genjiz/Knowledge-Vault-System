"""采集源身份统一与源配置字段

- crawl_task / raw_issue：source_type 值域改为真实采集源 id，新增 region 列，
  历史数据 domestic → ncpssd、foreign → elsevier
- raw_paper：新增 doi 列（官网源可提供 DOI）
- journal_source_config：新增默认源与测试连接结果字段

Revision ID: a3f7c1d92e05
Revises: c9b826cfa1c0
Create Date: 2026-09-03 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f7c1d92e05'
down_revision = 'c9b826cfa1c0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('crawl_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('region', sa.String(length=20), nullable=True))

    op.execute("UPDATE crawl_task SET source_type = 'ncpssd', region = 'domestic' WHERE source_type = 'domestic'")
    op.execute("UPDATE crawl_task SET source_type = 'elsevier', region = 'foreign' WHERE source_type = 'foreign'")

    with op.batch_alter_table('raw_issue', schema=None) as batch_op:
        batch_op.add_column(sa.Column('region', sa.String(length=20), nullable=True))

    op.execute("UPDATE raw_issue SET source_type = 'ncpssd', region = 'domestic' WHERE source_type = 'domestic'")
    op.execute("UPDATE raw_issue SET source_type = 'elsevier', region = 'foreign' WHERE source_type = 'foreign'")

    with op.batch_alter_table('raw_paper', schema=None) as batch_op:
        batch_op.add_column(sa.Column('doi', sa.String(length=100), nullable=True))

    with op.batch_alter_table('journal_source_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_default', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('last_checked_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_check_status', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('last_check_message', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('journal_source_config', schema=None) as batch_op:
        batch_op.drop_column('last_check_message')
        batch_op.drop_column('last_check_status')
        batch_op.drop_column('last_checked_at')
        batch_op.drop_column('is_default')

    with op.batch_alter_table('raw_paper', schema=None) as batch_op:
        batch_op.drop_column('doi')

    with op.batch_alter_table('raw_issue', schema=None) as batch_op:
        batch_op.drop_column('region')

    op.execute("UPDATE raw_issue SET source_type = 'domestic' WHERE source_type = 'ncpssd'")
    op.execute("UPDATE raw_issue SET source_type = 'foreign' WHERE source_type = 'elsevier'")

    op.execute("UPDATE crawl_task SET source_type = 'domestic' WHERE source_type = 'ncpssd'")
    op.execute("UPDATE crawl_task SET source_type = 'foreign' WHERE source_type = 'elsevier'")

    with op.batch_alter_table('crawl_task', schema=None) as batch_op:
        batch_op.drop_column('region')
