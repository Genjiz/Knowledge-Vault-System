"""add issue expected paper count and normalize magtech urls

Revision ID: f6a1c2d3e4b5
Revises: 5703b05951aa
Create Date: 2026-09-09 12:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "f6a1c2d3e4b5"
down_revision = "5703b05951aa"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("raw_issue", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "expected_paper_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE raw_issue SET expected_paper_count = paper_count "
            "WHERE expected_paper_count = 0"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE raw_paper "
            "SET detail_url = replace("
            "detail_url, '/CN/abstract/article_', '/CN/abstract/abstract'"
            ") "
            "WHERE detail_url LIKE '%/CN/abstract/article_%'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE literature "
            "SET url = replace(url, '/CN/abstract/article_', '/CN/abstract/abstract') "
            "WHERE url LIKE '%/CN/abstract/article_%'"
        )
    )


def downgrade():
    # URL 规范化是数据修复，降级时不恢复已知无效的旧地址。
    with op.batch_alter_table("raw_issue", schema=None) as batch_op:
        batch_op.drop_column("expected_paper_count")
