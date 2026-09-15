"""为原始论文增加卷号和期号

Revision ID: 9c2d7e4f1a60
Revises: f6a1c2d3e4b5
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa


revision = "9c2d7e4f1a60"
down_revision = "f6a1c2d3e4b5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("raw_paper") as batch_op:
        batch_op.add_column(sa.Column("volume", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("issue", sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table("raw_paper") as batch_op:
        batch_op.drop_column("issue")
        batch_op.drop_column("volume")
