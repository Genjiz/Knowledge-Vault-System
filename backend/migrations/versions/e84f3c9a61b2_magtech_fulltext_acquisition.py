"""Magtech 官网全文采集

Revision ID: e84f3c9a61b2
Revises: d7b9e4a12f60
Create Date: 2026-09-07 17:00:00.000000

"""
import json
import re

from alembic import op
import sqlalchemy as sa


revision = "e84f3c9a61b2"
down_revision = "d7b9e4a12f60"
branch_labels = None
depends_on = None


_ARTICLE_ID_RE = re.compile(r"(?:article_|abstract)(\d+)\.shtml", re.IGNORECASE)


def _backfill_source_refs(connection):
    rows = connection.execute(
        sa.text(
            "SELECT rp.id, rp.detail_url FROM raw_paper rp "
            "JOIN raw_issue ri ON ri.id = rp.raw_issue_id "
            "WHERE ri.source_type = 'magtech'"
        )
    ).mappings()
    for row in rows:
        match = _ARTICLE_ID_RE.search(row["detail_url"] or "")
        if match:
            connection.execute(
                sa.text("UPDATE raw_paper SET source_ref_json = :value WHERE id = :id"),
                {
                    "value": json.dumps({"article_id": match.group(1)}, ensure_ascii=False),
                    "id": row["id"],
                },
            )


def upgrade():
    with op.batch_alter_table("raw_paper", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_ref_json", sa.Text(), nullable=True))

    with op.batch_alter_table("literature", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pdf_source_type", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("pdf_source_raw_paper_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("pdf_sha256", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("pdf_size_bytes", sa.BigInteger(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_literature_pdf_source_raw_paper_id_raw_paper"),
            "raw_paper",
            ["pdf_source_raw_paper_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "fulltext_task",
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("raw_issue_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("replace_existing", sa.Boolean(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("succeeded_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("progress_message", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["raw_issue_id"],
            ["raw_issue.id"],
            name=op.f("fk_fulltext_task_raw_issue_id_raw_issue"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fulltext_task")),
    )
    with op.batch_alter_table("fulltext_task", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fulltext_task_raw_issue_id"), ["raw_issue_id"])
        batch_op.create_index(batch_op.f("ix_fulltext_task_status"), ["status"])

    op.create_table(
        "fulltext_task_item",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("literature_id", sa.Integer(), nullable=True),
        sa.Column("raw_paper_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["literature_id"],
            ["literature.id"],
            name=op.f("fk_fulltext_task_item_literature_id_literature"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["raw_paper_id"],
            ["raw_paper.id"],
            name=op.f("fk_fulltext_task_item_raw_paper_id_raw_paper"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["fulltext_task.id"],
            name=op.f("fk_fulltext_task_item_task_id_fulltext_task"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fulltext_task_item")),
    )
    with op.batch_alter_table("fulltext_task_item", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fulltext_task_item_literature_id"), ["literature_id"])
        batch_op.create_index(batch_op.f("ix_fulltext_task_item_raw_paper_id"), ["raw_paper_id"])
        batch_op.create_index(batch_op.f("ix_fulltext_task_item_status"), ["status"])
        batch_op.create_index(batch_op.f("ix_fulltext_task_item_task_id"), ["task_id"])

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE literature SET pdf_source_type = 'user' "
            "WHERE pdf_path IS NOT NULL AND pdf_path != '' AND pdf_source_type IS NULL"
        )
    )
    _backfill_source_refs(connection)


def downgrade():
    with op.batch_alter_table("fulltext_task_item", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fulltext_task_item_task_id"))
        batch_op.drop_index(batch_op.f("ix_fulltext_task_item_status"))
        batch_op.drop_index(batch_op.f("ix_fulltext_task_item_raw_paper_id"))
        batch_op.drop_index(batch_op.f("ix_fulltext_task_item_literature_id"))
    op.drop_table("fulltext_task_item")

    with op.batch_alter_table("fulltext_task", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fulltext_task_status"))
        batch_op.drop_index(batch_op.f("ix_fulltext_task_raw_issue_id"))
    op.drop_table("fulltext_task")

    with op.batch_alter_table("literature", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("fk_literature_pdf_source_raw_paper_id_raw_paper"),
            type_="foreignkey",
        )
        batch_op.drop_column("pdf_size_bytes")
        batch_op.drop_column("pdf_sha256")
        batch_op.drop_column("pdf_source_raw_paper_id")
        batch_op.drop_column("pdf_source_type")

    with op.batch_alter_table("raw_paper", schema=None) as batch_op:
        batch_op.drop_column("source_ref_json")
