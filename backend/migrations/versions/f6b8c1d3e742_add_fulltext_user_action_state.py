"""增加全文任务人工处理状态

Revision ID: f6b8c1d3e742
Revises: e2f7c9a4b610
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "f6b8c1d3e742"
down_revision = "e2f7c9a4b610"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("fulltext_task_item") as batch_op:
        batch_op.add_column(sa.Column("action_url", sa.String(length=1000)))
        batch_op.add_column(sa.Column("failure_code", sa.String(length=50)))
        batch_op.create_index(
            "ix_fulltext_task_item_failure_code",
            ["failure_code"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("fulltext_task_item") as batch_op:
        batch_op.drop_index("ix_fulltext_task_item_failure_code")
        batch_op.drop_column("failure_code")
        batch_op.drop_column("action_url")
