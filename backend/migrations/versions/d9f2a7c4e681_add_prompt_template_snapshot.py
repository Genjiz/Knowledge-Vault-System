"""增加分析 Prompt 模板快照

Revision ID: d9f2a7c4e681
Revises: c4a8e6d2f713
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa


revision = "d9f2a7c4e681"
down_revision = "c4a8e6d2f713"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("paper_analysis") as batch_op:
        batch_op.add_column(sa.Column("prompt_template_snapshot", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("paper_analysis") as batch_op:
        batch_op.drop_column("prompt_template_snapshot")
