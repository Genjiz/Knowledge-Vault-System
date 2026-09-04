"""期刊增加显式区域字段

期刊区域（domestic/foreign）此前由已启用采集源推导；现改为期刊一等属性，
由用户在「期刊与采集源」页维护，决定可选源范围与论文语言语义。
回填依据已配置采集源：ncpssd/magtech → domestic，elsevier → foreign。

Revision ID: c4e2a9f81b37
Revises: a3f7c1d92e05
Create Date: 2026-09-04 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e2a9f81b37'
down_revision = 'a3f7c1d92e05'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('journal', schema=None) as batch_op:
        batch_op.add_column(sa.Column('region', sa.String(length=20), nullable=True))

    op.execute(
        "UPDATE journal SET region = 'domestic' WHERE id IN "
        "(SELECT journal_id FROM journal_source_config WHERE source_id IN ('ncpssd', 'magtech'))"
    )
    op.execute(
        "UPDATE journal SET region = 'foreign' WHERE region IS NULL AND id IN "
        "(SELECT journal_id FROM journal_source_config WHERE source_id = 'elsevier')"
    )


def downgrade():
    with op.batch_alter_table('journal', schema=None) as batch_op:
        batch_op.drop_column('region')
